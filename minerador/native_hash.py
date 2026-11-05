"""Lotes SHA-256 em OpenSSL nativo. Ausência da biblioteca mantém fallback Python."""
from __future__ import annotations

import ctypes
from pathlib import Path

LIBRARY = Path(__file__).with_name("_native_hash.so")


class NativeScanner:
    def __init__(self, prefix: bytes, target: int):
        if len(prefix) != 76 or not 0 <= target < 1 << 256:
            raise ValueError("Cabeçalho ou alvo inválido")
        lib = ctypes.CDLL(str(LIBRARY))
        self._scan = lib.scan_nonces
        self._scan.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32,
                               ctypes.c_uint32, ctypes.c_uint32,
                               ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32)]
        self._scan.restype = ctypes.c_int
        self._prefix = ctypes.create_string_buffer(prefix)
        self._target = ctypes.create_string_buffer(target.to_bytes(32, "little"))

    def scan(self, start: int, stride: int, limit: int) -> tuple[int, int | None]:
        found = ctypes.c_uint32()
        processed = ctypes.c_uint32()
        result = self._scan(self._prefix, self._target, start, stride, limit,
                            ctypes.byref(found), ctypes.byref(processed))
        if result < 0:
            raise ValueError("Parâmetros inválidos no scanner nativo")
        return processed.value, found.value if result == 1 else None
