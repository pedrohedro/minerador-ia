"""Confere o scanner opcional com uma prova de trabalho real."""
import pytest

from minerador import btc
from minerador.native_hash import LIBRARY, NativeScanner


@pytest.mark.skipif(not LIBRARY.exists(), reason="scanner nativo não compilado")
def test_native_scanner_genesis():
    txid = btc.hex_to_hash("4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b")
    header = btc.build_header(1, b"\0" * 32, btc.merkle_root([txid]),
                              1231006505, 0x1D00FFFF, 2083236893)
    scanner = NativeScanner(header[:76], btc.bits_to_target(0x1D00FFFF))
    assert scanner.scan(2083236892, 1, 1) == (1, None)
    assert scanner.scan(2083236892, 1, 2) == (2, 2083236893)
