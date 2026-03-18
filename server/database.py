import os
from dotenv import load_dotenv
from sqlmodel import SQLModel, Session, create_engine

load_dotenv()

# ── Connection URL ─────────────────────────────────────────────────────────────
# Accepts either a full DATABASE_URL or individual POSTGRESQL_* variables.
# Individual vars take priority so the new .env layout works out of the box.

_host     = os.getenv("POSTGRESQL_HOST",     "localhost")
_port     = os.getenv("POSTGRESQL_PORT",     "5432")
_db       = os.getenv("POSTGRESQL_DATABASE", "sam-septa-db")
_user     = os.getenv("POSTGRESQL_USERNAME", "postgres")
_password = os.getenv("POSTGRESQL_PASSWORD", "postgres")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{_user}:{_password}@{_host}:{_port}/{_db}",
)

engine = create_engine(DATABASE_URL, echo=False)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
