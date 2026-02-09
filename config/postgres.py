import os
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict

load_dotenv()


class PostgresConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    host: str
    port: int
    dbname: str
    user: str
    password: str

    @classmethod
    def from_env(cls) -> "PostgresConfig":
        return cls(
            host=os.environ["PG_HOST"],
            port=int(os.environ["PG_PORT"]),
            dbname=os.environ["PG_DB"],
            user=os.environ["PG_USER"],
            password=os.environ["PG_PASSWORD"],
        )
    