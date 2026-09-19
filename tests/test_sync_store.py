import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.civicbridge.sync_store import (
    initialize_sync_database,
    record_success,
    should_skip_record,
)


class SyncStoreTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        self.db_path = str(Path(self.temp_dir.name) / "sync.db")
        initialize_sync_database(self.db_path)

    def test_skip_decision_uses_last_successful_source_timestamp(self):
        source_id = "TEST-001"
        original_timestamp = datetime(2026, 9, 19, 12, 0)

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
                datetime(2026, 9, 19, 11, 0),
            )
        )
        self.assertFalse(
            should_skip_record(
                self.db_path,
                source_id,
                datetime(2026, 9, 19, 13, 0),
            )
        )

    def test_recording_newer_success_updates_existing_row(self):
        source_id = "TEST-001"

        record_success(
            self.db_path,
            source_id,
            datetime(2026, 9, 19, 12, 0),
            "CREATED",
        )
        record_success(
            self.db_path,
            source_id,
            datetime(2026, 9, 19, 13, 0),
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
        self.assertEqual(rows[0][1], "2026-09-19T13:00:00")
        self.assertEqual(rows[0][2], "UPDATED")

        synced_at = datetime.fromisoformat(rows[0][3])
        self.assertIsNotNone(synced_at.tzinfo)
