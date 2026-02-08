import os
import base64 

from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

load_dotenv()

class CryptoUtils:
    KEY_B64 = os.getenv("ENCRYPTION_KEY")

    if not KEY_B64:
        raise RuntimeError("ENCRYPTION_KEY missing in .env")

    KEY = base64.b64decode(KEY_B64)
    if len(KEY) != 32:
        raise RuntimeError(
            f"ENCRYPTION_KEY must decode to 32 bytes for AES-256. Got {len(KEY)} bytes."
        )

    def should_encrypt(key:str, encrypt_keys: set[str]) -> bool:
        return key in encrypt_keys

    @classmethod
    def encrypt_bytes(cls, plaintext: bytes, aad: bytes) -> str:
        aesgcm = AESGCM(cls.KEY)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, plaintext, aad)
        payload = b"v1" + nonce + ct
        return base64.b64encode(payload).decode("utf-8")

    @classmethod
    def decrypt_bytes(cls, payload_b64: str, aad: bytes) -> bytes:
        raw = base64.b64decode(payload_b64.encode("utf-8"))
        if raw[:2] != b"v1":
            raise ValueError("Not encrypted with expected format/version header")
        nonce = raw[2:14]
        ct = raw[14:]
        aesgcm = AESGCM(cls.KEY)
        return aesgcm.decrypt(nonce, ct, aad)