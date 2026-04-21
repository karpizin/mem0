import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.main import create_app
from app.performance_benchmark import run_performance_benchmark
from app.telemetry.metrics import reset_metrics
from app.workers.runner import WorkerRunner


class PerformanceBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "performance_benchmark.db")
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

    def test_run_performance_benchmark_returns_latency_and_density_metrics(self) -> None:
        report = run_performance_benchmark(
            self.client,
            namespace_suffix="component-perf",
            memory_count=30,
            query_count=3,
            job_drainer=WorkerRunner.run_pending_jobs,
            poll_seconds=0.01,
            max_wait_seconds=5.0,
        )

        self.assertEqual(report["memory_count"], 30)
        self.assertEqual(report["query_count"], 3)
        self.assertEqual(report["jobs_by_status"]["pending"], 0)
        self.assertEqual(len(report["results"]), 3)
        self.assertGreaterEqual(report["metrics"]["candidate_count"]["avg"], 30.0)
        self.assertGreaterEqual(report["metrics"]["selected_count"]["avg"], 1.0)
        self.assertGreaterEqual(report["metrics"]["brief_chars"]["avg"], 1.0)
        self.assertGreaterEqual(report["metrics"]["latency_ms"]["max"], report["metrics"]["latency_ms"]["min"])
