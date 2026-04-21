import os
import tempfile
import unittest

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.load_benchmark import run_load_benchmark
from app.telemetry.metrics import reset_metrics


class LoadBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "load_benchmark.db")
        os.environ["MEMORY_RUNTIME_POSTGRES_DSN"] = f"sqlite+pysqlite:///{self.db_path}"
        os.environ["MEMORY_RUNTIME_AUTO_CREATE_TABLES"] = "true"
        os.environ["MEMORY_RUNTIME_ENV"] = "test"
        get_settings.cache_clear()
        reset_database_caches()
        reset_metrics()
        Base.metadata.create_all(bind=get_engine())

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

    def test_run_load_benchmark_reports_concurrent_recall_summary(self) -> None:
        report = run_load_benchmark(
            namespace_suffix="component-load",
            memory_count=40,
            concurrency=4,
            rounds=3,
            scenario="balanced_runtime",
        )

        self.assertEqual(report["mode"], "in_process")
        self.assertEqual(report["memory_count"], 40)
        self.assertEqual(report["concurrency"], 4)
        self.assertEqual(report["rounds"], 3)
        self.assertEqual(report["total_requests"], 12)
        self.assertEqual(report["failures"], 0)
        self.assertEqual(report["failure_rate"], 0.0)
        self.assertGreater(report["throughput_rps"], 0.0)
        self.assertGreaterEqual(report["latency_ms"]["avg"], 0.0)
        self.assertGreaterEqual(report["selected_count_mean"], 1.0)
        self.assertGreaterEqual(report["brief_chars_mean"], 1.0)
