"""Troca de candidato quando o Bitcoin Core avisa sobre um bloco novo."""
from minerador.node_source import NodeSource
from minerador.rpc import RPCError


def test_waitfornewblock_refreshes_candidate_without_polling():
    class RPC:
        def __init__(self):
            self.calls = []

        def call(self, method, *args):
            self.calls.append((method, args))
            if method == "getbestblockhash":
                return "old"
            if method == "waitfornewblock":
                return {"hash": "new"}
            raise AssertionError(method)

    rpc = RPC()
    source = NodeSource(rpc, b"", log=lambda *_: None)
    refreshed = []

    def refresh():
        refreshed.append(True)
        if len(refreshed) == 2:
            source.stop()

    source.refresh = refresh
    source.running = True
    source._loop()

    assert len(refreshed) == 2
    assert rpc.calls[1] == ("waitfornewblock", (1000, "old"))
    assert len([call for call in rpc.calls if call[0] == "getbestblockhash"]) == 1


def test_missing_waitfornewblock_falls_back_to_polling():
    class RPC:
        def call(self, method, *args):
            if method == "getbestblockhash":
                return "old"
            source.stop()
            raise RPCError("Method not found", -32601)

    source = NodeSource(RPC(), b"", log=lambda *_: None)
    source.refresh = lambda: None
    source.running = True
    source._loop()

    assert source._wait_supported is False
