import pickle
from langgraph.checkpoint.postgres import PostgresSaver
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import Checkpoint, CheckpointMetadata, ChannelVersions

from .crypto import CryptoUtils


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

        encrypt_keys = set(config["configurable"].get("encrypt_keys", []))

        new_cv = {}

        for k, v in channel_values.items():
            if CryptoUtils.should_encrypt(k, encrypt_keys):
                raw = pickle.dumps(v, protocol=pickle.HIGHEST_PROTOCOL)
                enc = CryptoUtils.encrypt_bytes(raw, aad + b"|" + k.encode())
                new_cv[k]={"__enc__":enc,"__fmt__":"pickle"}
            else:
                new_cv[k] = v
        
        cp["channel_values"] = new_cv

        return super().put(config, cp, metadata, new_versions)
    
    def _decrypt_checkpoint(self, config: RunnableConfig, cp: dict) -> dict:
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        aad = f"{thread_id}|{checkpoint_ns}|channel_values".encode("utf-8")

        cv = cp.get("channel_values", {})
        if not isinstance(cv, dict):
            return cp

        new_cv = {}
        for k, v in cv.items():
            if isinstance(v, dict) and "__enc__" in v:
                raw = CryptoUtils.decrypt_bytes(v["__enc__"], aad + b"|" + k.encode())
                new_cv[k] = pickle.loads(raw)
            else:
                new_cv[k] = v

        new_cp = dict(cp)
        new_cp["channel_values"] = new_cv
        return new_cp


    def get_tuple(self, config: RunnableConfig):
        t = super().get_tuple(config)
        if t is None:
            return None
        
        new_cp = self._decrypt_checkpoint(config,t.checkpoint)

        try:
            t.checkpoint = new_cp
            return t
        except AttributeError:
            from langgraph.checkpoint.base import CheckpointTuple
            return CheckpointTuple(
                checkpoint=new_cp,
                metadata=t.metadata,
                config=t.config,
                parent_config=t.parent_config,    
            )    

    def list(self, config: RunnableConfig, *args, **kwargs):
        for t in super().list(config, *args, **kwargs):
            new_cp = self._decrypt_checkpoint(config, t.checkpoint)

            try:
                t.checkpoint = new_cp
                yield t
            except AttributeError:
                from langgraph.checkpoint.base import CheckpointTuple
                yield CheckpointTuple(
                    checkpoint=new_cp,
                    metadata=t.metadata,
                    config=t.config,
                    parent_config=t.parent_config,
                )