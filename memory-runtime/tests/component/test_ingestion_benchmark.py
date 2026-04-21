import os
import tempfile
import unittest

from app.config import get_settings
from app.database import Base, get_engine, reset_database_caches
from app.ingestion_benchmark import run_ingestion_benchmark
from app.telemetry.metrics import reset_metrics


class IngestionBenchmarkTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "ingestion_benchmark.db")
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

    def test_run_ingestion_benchmark_reports_backlog_and_drain(self) -> None:
        report = run_ingestion_benchmark(
            namespace_suffix="component-ingestion",
            memory_count=40,
            scenario="balanced_runtime",
            sample_every=10,
            max_wait_seconds=10.0,
        )

        self.assertEqual(report["mode"], "in_process")
        self.assertEqual(report["memory_count"], 40)
        self.assertEqual(report["total_events"], 40)
        self.assertGreater(report["ingest_throughput_eps"], 0.0)
        self.assertGreaterEqual(report["ingest_latency_ms"]["avg"], 0.0)
        self.assertGreaterEqual(report["peak_pending_jobs"], report["pending_after_ingest"])
        self.assertTrue(report["drained"])
        self.assertEqual(report["job_status_delta_after_drain"]["pending"], 0)
        self.assertGreaterEqual(report["job_status_delta_after_drain"]["completed"], 1)
        self.assertIn("memory_consolidation", report["job_type_delta_after_ingest"])
        self.assertGreaterEqual(len(report["sampled_pending_jobs"]), 1)

