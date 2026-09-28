import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.civicbridge.sync_store import (
    finish_run,
    get_last_successful_run_started_at,
    initialize_sync_database,
    record_success,
    should_skip_record,
    start_run,
)


class SyncStoreTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.db_path = str(Path(self.temp_dir.name) / "sync.db")
        initialize_sync_database(self.db_path)

    def test_skip_decision_uses_last_successful_source_timestamp(self):
        source_id = "TEST-001"
        original_timestamp = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)

        self.assertFalse(
            should_skip_record(
                self.db_path,
                source_id,
                original_timestamp,
            )
        )

        record_success(
            self.db_path,
            source_id,
            original_timestamp,
            "CREATED",
        )

        self.assertTrue(
            should_skip_record(
                self.db_path,
                source_id,
                original_timestamp,
            )
        )
        self.assertTrue(
            should_skip_record(
                self.db_path,
                source_id,
                datetime(2026, 9, 19, 11, 0, tzinfo=timezone.utc),
            )
        )
        self.assertFalse(
            should_skip_record(
                self.db_path,
                source_id,
                datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
            )
        )

    def test_recording_newer_success_updates_existing_row(self):
        source_id = "TEST-001"

        record_success(
            self.db_path,
            source_id,
            datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc),
            "CREATED",
        )
        record_success(
            self.db_path,
            source_id,
            datetime(2026, 9, 19, 13, 0, tzinfo=timezone.utc),
            "UPDATED",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                """
                SELECT
                    source_id,
                    source_updated_at,
                    destination_result,
                    synced_at
                FROM synced_records
                """
            ).fetchall()
        finally:
            conn.close()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], source_id)
        self.assertEqual(rows[0][1], "2026-09-19T13:00:00+00:00")
        self.assertEqual(rows[0][2], "UPDATED")

        synced_at = datetime.fromisoformat(rows[0][3])
        self.assertIsNotNone(synced_at.tzinfo)


    def test_start_run_creates_running_row(self):
        run_id = start_run(self.db_path)

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    run_id,
                    started_at,
                    finished_at,
                    status,
                    fetched,
                    unmatched,
                    created,
                    updated,
                    skipped,
                    error_message
                FROM integration_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], run_id)
        self.assertIsNotNone(datetime.fromisoformat(row[1]).tzinfo)
        self.assertIsNone(row[2])
        self.assertEqual(row[3], "RUNNING")
        self.assertEqual(row[4:9], (0, 0, 0, 0, 0))
        self.assertIsNone(row[9])

    def test_finish_run_records_successful_summary(self):
        run_id = start_run(self.db_path)
        summary = {
            "fetched": 10,
            "unmatched": 2,
            "created": 3,
            "updated": 1,
            "skipped": 4,
        }

        finish_run(
            self.db_path,
            run_id,
            "SUCCEEDED",
            summary,
        )

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT
                    finished_at,
                    status,
                    fetched,
                    unmatched,
                    created,
                    updated,
                    skipped,
                    error_message
                FROM integration_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertIsNotNone(row)
        self.assertIsNotNone(datetime.fromisoformat(row[0]).tzinfo)
        self.assertEqual(row[1], "SUCCEEDED")
        self.assertEqual(row[2:7], (10, 2, 3, 1, 4))
        self.assertIsNone(row[7])

    def test_finish_run_records_failure_and_error(self):
        run_id = start_run(self.db_path)
        summary = {
            "fetched": 5,
            "unmatched": 1,
            "created": 1,
            "updated": 0,
            "skipped": 2,
        }

        finish_run(
            self.db_path,
            run_id,
            "FAILED",
            summary,
            "SOAP service unavailable",
        )

        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                """
                SELECT status, fetched, error_message
                FROM integration_runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        finally:
            conn.close()

        self.assertEqual(
            row,
            ("FAILED", 5, "SOAP service unavailable"),
        )

    def test_finish_run_rejects_invalid_status_and_missing_run(self):
        summary = {
            "fetched": 0,
            "unmatched": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
        }

        with self.assertRaisesRegex(
            ValueError,
            "Status must be SUCCEEDED or FAILED",
        ):
            finish_run(
                self.db_path,
                1,
                "BROKEN",
                summary,
            )

        with self.assertRaisesRegex(
            ValueError,
            "Run ID not found: 999",
        ):
            finish_run(
                self.db_path,
                999,
                "FAILED",
                summary,
            )


    def test_last_successful_run_returns_none_when_no_success_exists(self):
        self.assertIsNone(
            get_last_successful_run_started_at(self.db_path)
        )

    def test_last_successful_run_ignores_newer_failed_run(self):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executemany(
                """
                INSERT INTO integration_runs (started_at, status)
                VALUES (?, ?)
                """,
                [
                    ("2026-09-24T10:00:00+00:00", "SUCCEEDED"),
                    ("2026-09-24T11:00:00+00:00", "SUCCEEDED"),
                    ("2026-09-24T12:00:00+00:00", "FAILED"),
                ],
            )
            conn.commit()
        finally:
            conn.close()

        result = get_last_successful_run_started_at(self.db_path)

        self.assertEqual(
            result,
            datetime.fromisoformat("2026-09-24T11:00:00+00:00"),
        )
