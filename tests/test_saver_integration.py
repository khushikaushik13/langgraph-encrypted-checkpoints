import psycopg

from config.postgres import PostgresConfig
from persistence.encrypted_postgres_saver import SimpleEncryptedPostgresSaver
from registration.validator import RegistrationValidator
from registration.graph import RegistrationGraphFactory


def test_encryption_in_db_and_plaintext_on_read():
    pg = PostgresConfig.from_env()

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

    validator = RegistrationValidator(required_fields={"name", "email", "pan"})
    graph = RegistrationGraphFactory(validator).compile(checkpointer=checkpointer)

    config = {
        "configurable": {
            "thread_id": "pytest_thread",
            "encrypt_keys": ["email", "pan"],
        }
    }

    graph.invoke(
        {"name": "Khushi", "email": "khushi@gmail.com", "pan": "ABCDE1234F"},
        config,
    )

    cur = conn.cursor()
    cur.execute(
        """
        SELECT encode(blob, 'escape')
        FROM checkpoint_blobs
        WHERE thread_id = %s AND channel = 'email'
        ORDER BY version DESC
        LIMIT 1
        """,
        ("pytest_thread",),
    )
    row = cur.fetchone()
    assert row is not None
    assert "__enc__" in row[0]

    latest = graph.get_state(config)
    assert latest.values["email"] == "khushi@gmail.com"
    assert latest.values["pan"] == "ABCDE1234F"

    conn.close()
