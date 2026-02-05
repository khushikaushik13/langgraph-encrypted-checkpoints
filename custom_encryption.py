import os
import base64
import pickle
from typing import Optional

from dotenv import load_dotenv
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, ChannelVersions

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


class SimpleEncryptedPostgresSaver(PostgresSaver):

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        aad = f"{thread_id}|{checkpoint_ns}|channel_values".encode("utf-8")

        cp = dict(checkpoint)
        channel_values = cp.get("channel_values", {})

        cv_bytes = pickle.dumps(channel_values, protocol=pickle.HIGHEST_PROTOCOL)
        enc = CryptoUtils.encrypt_bytes(cv_bytes, aad)

        cp["channel_values"] = {"__enc__": enc, "__fmt__": "pickle"}

        return super().put(config, cp, metadata, new_versions)

    def get_tuple(self, config: RunnableConfig):
        t = super().get_tuple(config)
        if t is None:
            return None

        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        aad = f"{thread_id}|{checkpoint_ns}|channel_values".encode("utf-8")

        cp = t.checkpoint
        cv = cp.get("channel_values", {})

        if isinstance(cv, dict) and "__enc__" in cv:
            cv_bytes = CryptoUtils.decrypt_bytes(cv["__enc__"], aad)
            channel_values = pickle.loads(cv_bytes)

            new_cp = dict(cp)
            new_cp["channel_values"] = channel_values

            try:
                t.checkpoint = new_cp
                return t
            except Exception:
                from langgraph.checkpoint.base import CheckpointTuple
                return CheckpointTuple(
                    checkpoint=new_cp,
                    metadata=t.metadata,
                    config=t.config,
                    parent_config=t.parent_config,
                )

        return t