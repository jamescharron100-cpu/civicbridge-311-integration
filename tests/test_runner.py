from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.runner import run_integration


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
    def test_counts_results_and_skips_unmatched_records(self):
        records = [
            raw_complaint("UNMATCHED-001", "1000000000"),
            raw_complaint("MATCHED-001", "2037710066"),
            raw_complaint("MATCHED-002", "2037710066"),
        ]
        endpoint = "http://127.0.0.1:8000/soap"

        with (
            patch(
                "src.civicbridge.runner.fetch_complaints",
                return_value=records,
            ) as mock_fetch,
            patch(
                "src.civicbridge.runner.send_maintenance_request",
                side_effect=["CREATED", "UPDATED"],
            ) as mock_send,
        ):
            summary = run_integration(endpoint, limit=3, bbl="2037710066")

        self.assertEqual(summary, {"fetched": 3, "unmatched": 1, "created": 1, "updated": 1})
        mock_fetch.assert_called_once_with(3, bbl="2037710066")
        self.assertEqual(mock_send.call_count, 2)

        first_request, first_endpoint = mock_send.call_args_list[0].args
        self.assertEqual(first_endpoint, endpoint)
        self.assertEqual(
            first_request,
            MaintenanceRequest(
                external_id="MATCHED-001",
                property_id="CB-001",
                category="HEATING",
                priority="HIGH",
                status="OPEN",
                description="HEAT/HOT WATER: Heat & hot water",
                reported_at=datetime(2026, 9, 16),
                source_updated_at=datetime(2026, 9, 16),
            ),
        )
        self.assertEqual(mock_send.call_args_list[1].args[0].external_id, "MATCHED-002")

    def test_empty_batch_returns_zero_counts(self):
        with (
            patch(
                "src.civicbridge.runner.fetch_complaints",
                return_value=[],
            ),
            patch(
                "src.civicbridge.runner.send_maintenance_request"
            ) as mock_send,
        ):
            summary = run_integration("http://127.0.0.1:8000/soap")

        self.assertEqual(summary, {"fetched": 0, "unmatched": 0, "created": 0, "updated": 0})
        mock_send.assert_not_called()
