"""Contadores e registro sobrevivem ao reinício do processo."""
import collections
import threading
from types import SimpleNamespace

from minerador import controller
from minerador import ai


def test_mining_history_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(controller, "MINING_STATE_FILE", tmp_path / "estado_mineracao.json")
    ctrl = controller.Controller.__new__(controller.Controller)
    ctrl.lock = threading.RLock()
    ctrl.events = collections.deque(maxlen=400)
    ctrl.checked_total = 12345
    ctrl._saved_hashes = 0
    ctrl.hasher = SimpleNamespace(total=12340)
    ctrl.log("Bloco candidato atualizado")

    restored = ctrl._load_mining_state()
    assert restored["checked_total"] == 12345
    assert restored["hashes"] == 12340
    assert restored["events"][0]["msg"] == "Bloco candidato atualizado"


def test_best_ai_guess_survives_restart(tmp_path, monkeypatch):
    monkeypatch.setattr(ai, "AI_HISTORY_FILE", tmp_path / "palpites_ia.json")
    monkeypatch.setattr(ai, "USAGE_FILE", tmp_path / "uso_ia.json")
    first = ai.Copilot(None)
    first._record(first.ai, {"nonce": 123, "hash": "0000" + "f" * 60,
                             "zeros_bits": 16})
    first.guesses.appendleft({"nonce": 123, "hash": "0000" + "f" * 60,
                              "zeros_bits": 16})
    first._save_history()

    restored = ai.Copilot(None)
    assert restored.ai["melhor"]["zeros_bits"] == 16
    assert restored.ai["total"] == 1
    assert restored.guesses[0]["nonce"] == 123
