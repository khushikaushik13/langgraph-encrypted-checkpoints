# tests/test_crypto.py

import pytest
from persistence.crypto import CryptoUtils


def test_encrypt_decrypt_roundtrip():
    aad = b"thread|ns|channel_values|email"
    plaintext = b"hello-world"

    ct = CryptoUtils.encrypt_bytes(plaintext, aad)
    out = CryptoUtils.decrypt_bytes(ct, aad)

    assert out == plaintext


def test_decrypt_fails_with_wrong_aad():
    aad = b"correct"
    ct = CryptoUtils.encrypt_bytes(b"secret", aad)

    with pytest.raises(Exception):
        CryptoUtils.decrypt_bytes(ct, b"wrong")


def test_ciphertext_tamper_fails():
    aad = b"aad"
    ct = CryptoUtils.encrypt_bytes(b"secret", aad)

    # modify first character
    tampered = ("A" if ct[0] != "A" else "B") + ct[1:]

    with pytest.raises(Exception):
        CryptoUtils.decrypt_bytes(tampered, aad)
