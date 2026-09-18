from unittest import TestCase
from unittest.mock import patch

from src.civicbridge.nyc311_client import (BASE_URL, SOURCE_FIELDS, fetch_complaints)


class NYC311ClientTests(TestCase):
    @patch("src.civicbridge.nyc311_client.requests.get")
    def test_fetches_citywide_without_bbl(self, mock_get):
        response = mock_get.return_value
        response.json.return_value = [{"unique_key": "TEST-001"}]

        result = fetch_complaints(limit=5)

        self.assertEqual(result, [{"unique_key": "TEST-001"}])
        response.raise_for_status.assert_called_once_with()
        mock_get.assert_called_once_with(
            BASE_URL,
            params={
                "$limit": 5,
                "$order": "created_date DESC",
                "$where": (
                    "complaint_type IN "
                    "('HEAT/HOT WATER', 'PLUMBING', 'ELEVATOR')"
                ),
                "$select": ", ".join(SOURCE_FIELDS),
            },
            timeout=10,
        )

    @patch("src.civicbridge.nyc311_client.requests.get")
    def test_adds_quoted_bbl_filter(self, mock_get):
        mock_get.return_value.json.return_value = []

        fetch_complaints(limit=10, bbl="2037710066")

        self.assertEqual(
            mock_get.call_args.kwargs["params"]["$where"],
            "complaint_type IN "
            "('HEAT/HOT WATER', 'PLUMBING', 'ELEVATOR')"
            " AND bbl = '2037710066'",
        )

    @patch("src.civicbridge.nyc311_client.requests.get")
    def test_rejects_invalid_bbl_before_http_request(self, mock_get):
        for bbl in ("", "123", "20377100667", "203771006X", "２０３７７１００６６"):
            with self.subTest(bbl=bbl):
                with self.assertRaisesRegex(ValueError, "BBL must contain exactly 10 digits"):
                    fetch_complaints(bbl=bbl)

        mock_get.assert_not_called()
