from __future__ import annotations

from functools import lru_cache
import logging
from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.logging_utils import log_event


class Base(DeclarativeBase):
    pass


logger = logging.getLogger(__name__)


def _build_engine(database_url: str) -> Engine:
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
        if database_url.endswith(":memory:"):
            return create_engine(
                database_url,
                connect_args=connect_args,
                poolclass=StaticPool,
            )
        return create_engine(database_url, connect_args=connect_args)
    return create_engine(database_url)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    return _build_engine(settings.database_url)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_database() -> None:
    from app.models import agent, audit_log, episode, job, memory_event, memory_space, memory_unit, namespace  # noqa: F401

    engine = get_engine()
    database_url = get_settings().database_url

    if database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        log_event(logger, "database.schema_initialized", strategy="metadata.create_all", database="sqlite")
        return

    table_names = _table_names(engine)
    if not table_names:
        _run_alembic_upgrade(database_url)
        log_event(logger, "database.schema_initialized", strategy="alembic.upgrade", database="non-sqlite")
        return

    if "alembic_version" in table_names:
        _run_alembic_upgrade(database_url)
        log_event(logger, "database.schema_initialized", strategy="alembic.upgrade", database="managed")
        return

    Base.metadata.create_all(bind=engine)
    _reconcile_bootstrap_schema(engine)
    _stamp_alembic_head(database_url)
    log_event(
        logger,
        "database.schema_initialized",
        strategy="bootstrap_reconcile_and_stamp",
        database="non-sqlite",
        tables=sorted(table_names),
    )


def reset_database_caches() -> None:
    get_engine.cache_clear()
    get_session_factory.cache_clear()


def _alembic_config(database_url: str) -> Config:
    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _run_alembic_upgrade(database_url: str) -> None:
    command.upgrade(_alembic_config(database_url), "head")


def _stamp_alembic_head(database_url: str) -> None:
    command.stamp(_alembic_config(database_url), "head")


def _table_names(engine: Engine) -> set[str]:
    return set(inspect(engine).get_table_names())


def _reconcile_bootstrap_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "memory_events" not in table_names:
        return

    column_names = {column["name"] for column in inspector.get_columns("memory_events")}
    if "event_origin" in column_names:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE memory_events ADD COLUMN IF NOT EXISTS event_origin VARCHAR(50)"))
        connection.execute(text("UPDATE memory_events SET event_origin = 'user_input' WHERE event_origin IS NULL"))
        connection.execute(text("ALTER TABLE memory_events ALTER COLUMN event_origin SET NOT NULL"))
        connection.execute(
            text("CREATE INDEX IF NOT EXISTS ix_memory_events_event_origin ON memory_events (event_origin)")
        )

    log_event(
        logger,
        "database.schema_reconciled",
        table="memory_events",
        change="added_event_origin",
    )
