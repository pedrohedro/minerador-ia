"""Contadores e registro sobrevivem ao reinício do processo."""
import collections
import threading
from types import SimpleNamespace

from minerador import controller


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
