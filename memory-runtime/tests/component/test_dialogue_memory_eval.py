from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.dialogue_eval import load_scenarios, run_dialogue_memory_eval
from app.main import create_app
from app.workers.runner import WorkerRunner


class DialogueMemoryEvalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "dialogue_eval.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        os.environ["MEMORY_RUNTIME_AUTO_CREATE_TABLES"] = "true"
        os.environ["MEMORY_RUNTIME_ENV"] = "test"
        get_settings.cache_clear()
        reset_database_caches()
        Base.metadata.create_all(bind=get_engine())
        self.client = TestClient(create_app())

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        for key in (
            "MEMORY_RUNTIME_POSTGRES_DSN",
            "MEMORY_RUNTIME_AUTO_CREATE_TABLES",
            "MEMORY_RUNTIME_ENV",
        ):
            os.environ.pop(key, None)
        get_settings.cache_clear()
        reset_database_caches()

    def test_dialogue_memory_eval_passes_curated_manual_scenarios(self) -> None:
        fixture_path = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "evals"
            / "dialogue_memory_scenarios.json"
        )

        report = run_dialogue_memory_eval(
            self.client,
            engine=get_engine(),
            scenarios=load_scenarios(fixture_path),
            job_drainer=WorkerRunner.run_pending_jobs,
        )

        self.assertEqual(report["total"], 5)
        self.assertEqual(report["failed"], 0)
        self.assertEqual(report["passed"], 5)
        self.assertEqual(report["metrics"]["storage_pass_rate"], 1.0)
        self.assertEqual(report["metrics"]["audit_pass_rate"], 1.0)
        self.assertEqual(report["metrics"]["recall_pass_rate"], 1.0)
        self.assertTrue(all(item["passed"] for item in report["results"]))
        self.assertTrue(all(item["annotation_notes"] for item in report["results"]))
