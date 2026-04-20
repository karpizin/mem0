from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import database


class DatabaseInitTests(unittest.TestCase):
    @patch.object(database.Base.metadata, "create_all")
    @patch("app.database.get_engine", return_value=object())
    @patch("app.database.get_settings", return_value=SimpleNamespace(database_url="sqlite+pysqlite:///./test.db"))
    def test_init_database_uses_create_all_for_sqlite(self, _settings, _engine, create_all) -> None:
        with patch("app.database._run_alembic_upgrade") as upgrade:
            database.init_database()

        create_all.assert_called_once()
        upgrade.assert_not_called()

    @patch("app.database.get_engine", return_value=object())
    @patch(
        "app.database.get_settings",
        return_value=SimpleNamespace(database_url="postgresql+psycopg://postgres:postgres@db/memory_runtime"),
    )
    @patch("app.database._table_names", return_value=set())
    def test_init_database_runs_alembic_upgrade_for_empty_non_sqlite_database(
        self,
        _table_names,
        _settings,
        _engine,
    ) -> None:
        with patch("app.database._run_alembic_upgrade") as upgrade:
            database.init_database()

        upgrade.assert_called_once_with("postgresql+psycopg://postgres:postgres@db/memory_runtime")

    @patch.object(database.Base.metadata, "create_all")
    @patch("app.database.get_engine", return_value=object())
    @patch(
        "app.database.get_settings",
        return_value=SimpleNamespace(database_url="postgresql+psycopg://postgres:postgres@db/memory_runtime"),
    )
    @patch("app.database._table_names", return_value={"namespaces", "memory_events"})
    def test_init_database_reconciles_bootstrap_schema_without_alembic_history(
        self,
        _table_names,
        _settings,
        _engine,
        create_all,
    ) -> None:
        with patch("app.database._reconcile_bootstrap_schema") as reconcile, patch(
            "app.database._stamp_alembic_head"
        ) as stamp, patch("app.database._run_alembic_upgrade") as upgrade:
            database.init_database()

        create_all.assert_called_once()
        reconcile.assert_called_once()
        stamp.assert_called_once_with("postgresql+psycopg://postgres:postgres@db/memory_runtime")
        upgrade.assert_not_called()

    @patch("app.database.get_engine", return_value=object())
    @patch(
        "app.database.get_settings",
        return_value=SimpleNamespace(database_url="postgresql+psycopg://postgres:postgres@db/memory_runtime"),
    )
    @patch("app.database._table_names", return_value={"alembic_version", "namespaces", "memory_events"})
    def test_init_database_upgrades_managed_non_sqlite_database(
        self,
        _table_names,
        _settings,
        _engine,
    ) -> None:
        with patch("app.database._run_alembic_upgrade") as upgrade:
            database.init_database()

        upgrade.assert_called_once_with("postgresql+psycopg://postgres:postgres@db/memory_runtime")


class LocalRuntimeClientTests(unittest.TestCase):
    def test_local_runtime_client_disables_proxy_inheritance(self) -> None:
        from app.http_client import create_local_runtime_client

        with create_local_runtime_client(base_url="http://127.0.0.1:8080", timeout=5.0) as client:
            self.assertFalse(client._trust_env)
