import sqlite3
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from src.civicbridge.case_store import initialize_database, upsert_case


class CaseStoreTests(TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = str(Path(self.temp_dir.name) / "cases.db")
        initialize_database(self.db_path)
        self.fields = {
            "ExternalId": "STORE-TEST-001",
            "PropertyId": "CB-001",
            "Category": "HEATING",
            "Priority": "HIGH",
            "Status": "OPEN",
            "Description": "Heat & hot water",
            "ReportedAt": "2026-09-16T00:00:00",
            "SourceUpdatedAt": "2026-09-16T00:00:00",
        }

    def read_cases(self):
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute(
                """
                SELECT external_id, property_id, category, priority,
                       status, description, reported_at, source_updated_at
                FROM maintenance_cases
                ORDER BY external_id
                """
            ).fetchall()
        finally:
            conn.close()

    def test_creates_case_and_persists_all_fields(self):
        self.assertEqual(upsert_case(self.db_path, self.fields), "CREATED")
        self.assertEqual(
            self.read_cases(),
            [(
                "STORE-TEST-001",
                "CB-001",
                "HEATING",
                "HIGH",
                "OPEN",
                "Heat & hot water",
                "2026-09-16T00:00:00",
                "2026-09-16T00:00:00",
            )],
        )

    def test_updates_existing_case_without_duplicate(self):
        upsert_case(self.db_path, self.fields)
        changed = {
            **self.fields,
            "PropertyId": "CB-002",
            "Category": "PLUMBING",
            "Priority": "NORMAL",
            "Status": "CLOSED",
            "Description": "Leak repaired",
            "ReportedAt": "2026-09-15T00:00:00",
            "SourceUpdatedAt": "2026-09-18T00:00:00",
        }

        self.assertEqual(upsert_case(self.db_path, changed), "UPDATED")
        self.assertEqual(
            self.read_cases(),
            [(
                "STORE-TEST-001",
                "CB-002",
                "PLUMBING",
                "NORMAL",
                "CLOSED",
                "Leak repaired",
                "2026-09-15T00:00:00",
                "2026-09-18T00:00:00",
            )],
        )

    def test_initializing_again_preserves_existing_case(self):
        upsert_case(self.db_path, self.fields)

        initialize_database(self.db_path)

        self.assertEqual(len(self.read_cases()), 1)
        self.assertEqual(upsert_case(self.db_path, self.fields), "UPDATED")

    def test_failed_update_preserves_case_and_allows_retry(self):
        upsert_case(self.db_path, self.fields)
        before = self.read_cases()
        invalid = {**self.fields, "Description": None}

        with self.assertRaises(sqlite3.IntegrityError):
            upsert_case(self.db_path, invalid)

        self.assertEqual(self.read_cases(), before)

        corrected = {**self.fields, "Description": "Heating restored"}
        self.assertEqual(upsert_case(self.db_path, corrected), "UPDATED")
        self.assertEqual(self.read_cases()[0][5], "Heating restored")
