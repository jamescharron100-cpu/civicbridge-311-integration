import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.runner import run_integration
from src.civicbridge.sync_store import should_skip_record, get_last_successful_run_started_at


def raw_complaint(source_id, bbl):
    return {
        "unique_key": source_id,
        "created_date": "2026-09-16T00:00:00",
        "agency": "HPD",
        "complaint_type": "HEAT/HOT WATER",
        "status": "Open",
        "descriptor": "Heat & hot water",
        "bbl": bbl,
    }


class RunnerTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.sync_db_path = str(
            Path(self.temp_dir.name) / "sync.db"
        )

    def test_counts_results_and_skips_successful_records_on_next_run(self):
        records = [
            raw_complaint("UNMATCHED-001", "1000000000"),
            raw_complaint("MATCHED-001", "2037710066"),
            raw_complaint("MATCHED-002", "2037710066"),
        ]
        endpoint = "http://127.0.0.1:8000/soap"

        with (
            patch(
                "src.civicbridge.runner.fetch_complaint_pages",
                return_value=records,
            ) as mock_fetch,
            patch(
                "src.civicbridge.runner.send_maintenance_request",
                side_effect=["CREATED", "UPDATED"],
            ) as mock_send,
        ):
            first_summary = run_integration(
                endpoint,
                self.sync_db_path,
                page_size=3,
                max_pages=2,
                bbl="2037710066",
            )

            first_checkpoint = get_last_successful_run_started_at(self.sync_db_path)

            second_summary = run_integration(
                endpoint,
                self.sync_db_path,
                page_size=3,
                max_pages=2,
                bbl="2037710066",
            )

        self.assertEqual(
            first_summary,
            {
                "fetched": 3,
                "unmatched": 1,
                "created": 1,
                "updated": 1,
                "skipped": 0,
            },
        )
        self.assertEqual(
            second_summary,
            {
                "fetched": 3,
                "unmatched": 1,
                "created": 0,
                "updated": 0,
                "skipped": 2,
            },
        )

        self.assertEqual(mock_fetch.call_count, 2)
        self.assertIsNotNone(first_checkpoint)

        self.assertEqual(
            mock_fetch.call_args_list[0].kwargs,
            {
                "page_size": 3,
                "max_pages": 2,
                "bbl": "2037710066",
                "updated_after": None,
            },
        )
        self.assertEqual(
            mock_fetch.call_args_list[1].kwargs,
            {
                "page_size": 3,
                "max_pages": 2,
                "bbl": "2037710066",
                "updated_after": first_checkpoint,
            },
        )

    def test_failed_send_is_not_recorded_as_successful(self):
        record = raw_complaint(
            "MATCHED-003",
            "2037710066",
        )

        with (
            patch(
                "src.civicbridge.runner.fetch_complaint_pages",
                return_value=[record],
            ),
            patch(
                "src.civicbridge.runner.send_maintenance_request",
                side_effect=RuntimeError("SOAP unavailable"),
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "SOAP unavailable",
            ):
                run_integration(
                    "http://127.0.0.1:8000/soap",
                    self.sync_db_path,
                )

        self.assertFalse(
            should_skip_record(
                self.sync_db_path,
                "MATCHED-003",
                datetime(2026, 9, 16),
            )
        )

    def test_empty_batch_returns_zero_counts(self):
        with (
            patch(
                "src.civicbridge.runner.fetch_complaint_pages",
                return_value=[],
            ),
            patch(
                "src.civicbridge.runner.send_maintenance_request",
            ) as mock_send,
        ):
            summary = run_integration(
                "http://127.0.0.1:8000/soap",
                self.sync_db_path,
            )

        self.assertEqual(
            summary,
            {
                "fetched": 0,
                "unmatched": 0,
                "created": 0,
                "updated": 0,
                "skipped": 0,
            },
        )
        mock_send.assert_not_called()


    def test_successful_integration_run_is_recorded(self):
        with patch(
            "src.civicbridge.runner.fetch_complaint_pages",
            return_value=[],
        ):
            run_integration(
                "http://127.0.0.1:8000/soap",
                self.sync_db_path,
            )

        conn = sqlite3.connect(self.sync_db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    status,
                    fetched,
                    unmatched,
                    created,
                    updated,
                    skipped,
                    error_message,
                    finished_at
                FROM integration_runs
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(row[0], "SUCCEEDED")
        self.assertEqual(row[1:6], (0, 0, 0, 0, 0))
        self.assertIsNone(row[6])
        self.assertIsNotNone(row[7])

    def test_fetch_failure_is_recorded_and_reraised(self):
        with patch(
            "src.civicbridge.runner.fetch_complaint_pages",
            side_effect=RuntimeError("NYC 311 unavailable"),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "NYC 311 unavailable",
            ):
                run_integration(
                    "http://127.0.0.1:8000/soap",
                    self.sync_db_path,
                )

        conn = sqlite3.connect(self.sync_db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    status,
                    fetched,
                    error_message,
                    finished_at
                FROM integration_runs
                """
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(row[0], "FAILED")
        self.assertEqual(row[1], 0)
        self.assertEqual(row[2], "NYC 311 unavailable")
        self.assertIsNotNone(row[3])
