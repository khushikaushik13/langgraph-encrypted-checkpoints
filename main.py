import psycopg

from config.postgres import PostgresConfig
from persistence.encrypted_postgres_saver import SimpleEncryptedPostgresSaver
from registration.validator import RegistrationValidator
from registration.graph import RegistrationGraphFactory
from registration.state import RegistrationState


def main():
    patches = [
        {"name": "K", "email": "khushi@gmail.com", "pan": "ABCDE1234"},
        {"name": "Khushi", "pan": "ABCDE1234F"},
        {"phone": "9999999999", "dob": "01-01-2004"},
    ]

    pg = PostgresConfig.from_env()

    config = {
        "configurable": {
            "thread_id": "reg_demo_1",
            "encrypt_keys": ["pan", "email"],
        }
    }

    validator = RegistrationValidator(required_fields={"name", "email", "pan"})
    factory = RegistrationGraphFactory(validator)

    conn = psycopg.connect(
        host=pg.host,
        port=pg.port,
        dbname=pg.dbname,
        user=pg.user,
        password=pg.password,
    )
    conn.autocommit = True

    checkpointer = SimpleEncryptedPostgresSaver(conn)
    checkpointer.setup()

    graph = factory.compile(checkpointer=checkpointer)

    state = None
    for i, patch in enumerate(patches, 1):
        state = graph.invoke(patch, config)
        print(f"\nINVOKE #{i}")

    if isinstance(state, RegistrationState):
        print("missing_fields:", state.missing_fields)
        print("validation_errors:", state.validation_errors)
    else:
        print("Graph ended. Current state:", state)

    hist = list(graph.get_state_history(config))
    print(f"\nCheckpoint count for thread_id=reg_demo_1: {len(hist)}")

    latest = graph.get_state(config)
    print("Latest snapshot keys:", list(latest.values.keys()))


if __name__ == "__main__":
    main()