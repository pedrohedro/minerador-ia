"""Busca contínua de prova de trabalho, independente das chamadas à IA."""
from __future__ import annotations

import hashlib
import multiprocessing as mp
import os
import queue
import secrets
import struct
import threading
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from . import btc
from .native_hash import NativeScanner

DAY_WORKERS = 2
TIMEZONE = ZoneInfo("America/Sao_Paulo")
BATCH = 8192
NATIVE_BATCH = 262144


def worker_schedule(enabled: bool, now: datetime | None = None) -> tuple[int, str]:
    if os.environ.get("MINERADOR_WORKERS", "").strip().lower() == "all":
        return max(1, os.cpu_count() or 1), "integral"
    hour = (now or datetime.now(TIMEZONE)).astimezone(TIMEZONE).hour
    night = hour >= 20 or hour < 9
    return (max(DAY_WORKERS, os.cpu_count() or DAY_WORKERS) if enabled and night
            else DAY_WORKERS), ("noite" if night else "dia")


def _worker(job, index: int, count: int, extra: bytes, stop, reports) -> None:
    # A IA usa extra nonce zero; cada processo usa um valor distinto.
    prefix = job.header(extra, 0)[:76]
    first = hashlib.sha256(prefix)
    try:
        scanner = NativeScanner(prefix, job.target)
    except OSError:
        scanner = None
    target = job.target
    nonce = index
    checked = 0
    while not stop.is_set():
        if scanner is not None:
            if nonce > 0xFFFFFFFF:
                extra = (int.from_bytes(extra, "little") + count).to_bytes(8, "little")
                prefix = job.header(extra, 0)[:76]
                scanner = NativeScanner(prefix, target)
                nonce = index
            processed, found = scanner.scan(nonce, count, min(NATIVE_BATCH, (0xFFFFFFFF - nonce) // count + 1))
            checked += processed
            nonce += processed * count
            if found is not None:
                reports.put(("found", job.job_id, extra, found, checked))
                return
            reports.put(("progress", job.job_id, checked))
            checked = 0
            continue
        for _ in range(BATCH):
            if nonce > 0xFFFFFFFF:
                extra = (int.from_bytes(extra, "little") + count).to_bytes(8, "little")
                prefix = job.header(extra, 0)[:76]
                first = hashlib.sha256(prefix)
                nonce = index
            h = first.copy()
            h.update(struct.pack("<I", nonce))
            digest = hashlib.sha256(h.digest()).digest()
            checked += 1
            if btc.hash_to_int(digest) <= target:
                reports.put(("found", job.job_id, extra, nonce, checked))
                return
            nonce += count
        reports.put(("progress", job.job_id, checked))
        checked = 0


class Hasher:
    def __init__(self, controller):
        self.ctrl = controller
        self.ctx = mp.get_context("spawn")
        self.processes = []
        self.stop_event = None
        self.reports = None
        self.job_id = None
        self.worker_count = 0
        self.generation = 0
        self.total = 0
        self.started = time.monotonic()
        self.last_count = 0
        self.rate = 0.0
        self._quit = threading.Event()
        threading.Thread(target=self._loop, daemon=True, name="hash-manager").start()

    def _stop_workers(self) -> None:
        if self.stop_event:
            self.stop_event.set()
        for process in self.processes:
            process.join(timeout=0.5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=0.5)
        self.processes = []
        self.worker_count = 0
        if self.reports:
            self.reports.close()
        self.reports = None
        self.stop_event = None

    def _start_workers(self, job, count: int) -> None:
        self.generation += 1
        base = secrets.randbelow((1 << 64) - count * 2) + 1
        self.worker_count = count
        self.stop_event = self.ctx.Event()
        self.reports = self.ctx.Queue()
        self.processes = [self.ctx.Process(target=_worker,
                          args=(job, i, count, (base + i).to_bytes(8, "little"), self.stop_event, self.reports), daemon=True)
                          for i in range(count)]
        for process in self.processes:
            process.start()
        self.ctrl.log(f"Hashing contínuo iniciado: {count} trabalhadores na altura {job.height}.")

    def _loop(self) -> None:
        while not self._quit.is_set():
            job = self.ctrl.current_job if self.ctrl.source and self.ctrl.source.connected else None
            job_id = job.job_id if job and job.job_id not in self.ctrl.solved_jobs else None
            desired, _ = worker_schedule(self.ctrl.config.get("hashing_noturno", False))
            if job_id != self.job_id or (job_id and desired != self.worker_count):
                self._stop_workers()
                self.job_id = job_id
                if job:
                    self._start_workers(job, desired)
            elif job_id and self.processes and not any(p.is_alive() for p in self.processes):
                # Um achado transmitido pode ser recusado; retome a busca nesse caso.
                self._stop_workers()
                self._start_workers(job, desired)
            if self.reports:
                try:
                    item = self.reports.get(timeout=0.25)
                except queue.Empty:
                    item = None
                if item and item[1] == self.job_id:
                    count = item[-1]
                    self.total += count
                    self.ctrl.checked_total += count
                    if item[0] == "found":
                        _, _, extra, nonce, _ = item
                        if self.ctrl.current_job is job:
                            self.ctrl.try_nonce(job, nonce, origin="hashing contínuo", extranonce=extra)
            else:
                self._quit.wait(0.25)
            elapsed = time.monotonic() - self.started
            if elapsed >= 3:
                self.rate = (self.total - self.last_count) / elapsed
                self.last_count = self.total
                self.started = time.monotonic()
        self._stop_workers()

    def status(self) -> dict:
        desired, period = worker_schedule(self.ctrl.config.get("hashing_noturno", False))
        return {"trabalhadores": sum(p.is_alive() for p in self.processes),
                "hashes": self.total, "hashes_por_segundo": round(self.rate, 1),
                "altura_ativa": self.ctrl.current_job.height if self.job_id and self.ctrl.current_job else None,
                "trabalhadores_programados": desired, "periodo": period}

    def shutdown(self) -> None:
        self._quit.set()
