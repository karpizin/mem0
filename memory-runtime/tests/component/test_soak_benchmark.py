import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.main import create_app
from app.soak_benchmark import run_soak_benchmark
from app.telemetry.metrics import reset_metrics


class SoakBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "soak_benchmark.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        os.environ["MEMORY_RUNTIME_AUTO_CREATE_TABLES"] = "true"
        os.environ["MEMORY_RUNTIME_ENV"] = "test"
        get_settings.cache_clear()
        reset_database_caches()
        reset_metrics()
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
        reset_metrics()

    def test_run_soak_benchmark_reports_repeated_recall_summary(self) -> None:
        report = run_soak_benchmark(
            self.client,
            namespace_suffix="component-soak",
            memory_count=50,
            iterations=8,
            scenario="balanced_runtime",
        )

        self.assertEqual(report["scenario"], "balanced_runtime")
        self.assertEqual(report["memory_count"], 50)
        self.assertEqual(report["iterations"], 8)
        self.assertEqual(report["failures"], 0)
        self.assertEqual(report["failure_rate"], 0.0)
        self.assertGreaterEqual(report["latency_ms"]["avg"], 0.0)
        self.assertGreaterEqual(report["selected_count_mean"], 1.0)
        self.assertGreaterEqual(report["brief_chars_mean"], 1.0)
