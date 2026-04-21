import os
import tempfile
import unittest

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.scale_benchmark import run_scale_benchmark
from app.telemetry.metrics import reset_metrics


class ScaleBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "scale_benchmark.db")
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

    def test_run_scale_benchmark_returns_trend_summary_for_multiple_memory_counts(self) -> None:
        report = run_scale_benchmark(
            memory_counts=[40, 80],
            namespace_prefix="component-scale",
            concurrency=4,
            rounds=2,
            scenario="balanced_runtime",
        )

        self.assertEqual(report["mode"], "in_process")
        self.assertEqual(report["memory_counts"], [40, 80])
        self.assertEqual(report["concurrency"], 4)
        self.assertEqual(report["rounds"], 2)
        self.assertEqual(len(report["reports"]), 2)
        self.assertEqual(len(report["trend_summary"]), 2)
        self.assertEqual(report["trend_summary"][0]["memory_count"], 40)
        self.assertEqual(report["trend_summary"][1]["memory_count"], 80)
        self.assertGreater(report["trend_summary"][0]["avg_latency_ms"], 0.0)
        self.assertGreaterEqual(report["trend_summary"][0]["candidate_fetch_ms"], 0.0)
        self.assertGreaterEqual(report["trend_summary"][1]["feedback_lookup_ms"], 0.0)
