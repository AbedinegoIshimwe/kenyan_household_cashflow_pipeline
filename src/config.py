"""PostgreSQL configuration and connection helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = PROJECT_ROOT / ".env"
EXPECTED_DATABASE = "kenya_cashflow_db"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    username: str
    password: str = field(repr=False)


def get_database_settings() -> DatabaseSettings:
    """Load required database settings from the project-root .env file."""
    load_dotenv(ENV_FILE)
    names = {
        "host": "PG_HOST",
        "port": "PG_PORT",
        "database": "PG_DATABASE",
        "username": "PG_USER",
        "password": "PG_PASSWORD",
    }
    values = {key: os.getenv(env_name) for key, env_name in names.items()}
    missing = [
        env_name
        for key, env_name in names.items()
        if not values[key] or not values[key].strip()
    ]
    if missing:
        raise RuntimeError(
            "Missing required .env settings: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in the local values."
        )
    if values["password"] == "CHANGE_ME":
        raise RuntimeError(
            "PG_PASSWORD in the project-root .env is still CHANGE_ME. "
            "Set your local PostgreSQL password there."
        )
    if values["database"] != EXPECTED_DATABASE:
        raise RuntimeError(
            f"PG_DATABASE must be {EXPECTED_DATABASE}; refusing to use another database."
        )

    try:
        port = int(values["port"])
    except ValueError:
        raise RuntimeError("PG_PORT in .env must be an integer.") from None
    if not 1 <= port <= 65535:
        raise RuntimeError("PG_PORT in .env must be between 1 and 65535.")

    return DatabaseSettings(
        host=values["host"] or "",
        port=port,
        database=values["database"] or "",
        username=values["username"] or "",
        password=values["password"] or "",
    )


def create_database_engine(settings: DatabaseSettings | None = None) -> Engine:
    """Create a psycopg-backed SQLAlchemy engine with safely escaped credentials."""
    settings = settings or get_database_settings()
    url = URL.create(
        "postgresql+psycopg",
        username=settings.username,
        password=settings.password,
        host=settings.host,
        port=settings.port,
        database=settings.database,
    )
    return create_engine(url, pool_pre_ping=True)


def test_database_connection() -> str:
    """Print a password-free status and return the connected database name."""
    settings = get_database_settings()
    engine = create_database_engine(settings)
    try:
        with engine.connect() as connection:
            database_name = connection.execute(
                text("SELECT current_database()")
            ).scalar_one()
    except SQLAlchemyError:
        print(
            "PostgreSQL connection status: FAILED "
            f"(database={settings.database}, host={settings.host}, "
            f"port={settings.port})."
        )
        raise RuntimeError(
            "Could not connect to PostgreSQL. Check that the local service is "
            "running and that PG_HOST, PG_PORT, PG_DATABASE, PG_USER, and "
            "PG_PASSWORD in .env are correct."
        ) from None
    finally:
        engine.dispose()

    if database_name != settings.database:
        raise RuntimeError(
            "Connected to an unexpected database; no data was loaded."
        )
    print(
        "PostgreSQL connection status: OK "
        f"(database={database_name}, host={settings.host}, port={settings.port})."
    )
    return database_name


if __name__ == "__main__":
    test_database_connection()
