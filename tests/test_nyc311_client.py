from unittest import TestCase
from unittest.mock import call, patch

from src.civicbridge.nyc311_client import (BASE_URL, SOURCE_FIELDS, fetch_complaints, fetch_complaint_pages)


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
                "$order": "created_date DESC, unique_key DESC",
                "$where": (
                    "complaint_type IN "
                    "('HEAT/HOT WATER', 'PLUMBING', 'ELEVATOR')"
                ),
                "$select": ", ".join(SOURCE_FIELDS),
                "$offset": 0,
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


    @patch("src.civicbridge.nyc311_client.requests.get")
    def test_uses_requested_offset(self, mock_get):
        mock_get.return_value.json.return_value = []

        fetch_complaints(
            limit=25,
            offset=50,
        )

        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["$limit"], 25)
        self.assertEqual(params["$offset"], 50)
        self.assertEqual(
            params["$order"],
            "created_date DESC, unique_key DESC",
        )

    @patch("src.civicbridge.nyc311_client.requests.get")
    def test_rejects_invalid_pagination_before_http_request(
        self,
        mock_get,
    ):
        for limit in (0, -1):
            with self.subTest(limit=limit):
                with self.assertRaisesRegex(
                    ValueError,
                    "Limit must be greater than zero",
                ):
                    fetch_complaints(limit=limit)

        for offset in (-1, -100):
            with self.subTest(offset=offset):
                with self.assertRaisesRegex(
                    ValueError,
                    "Offset cannot be negative",
                ):
                    fetch_complaints(offset=offset)

        mock_get.assert_not_called()


    @patch("src.civicbridge.nyc311_client.fetch_complaints")
    def test_fetches_pages_until_short_page(self, mock_fetch):
        first_page = [
            {"unique_key": "TEST-001"},
            {"unique_key": "TEST-002"},
        ]
        second_page = [
            {"unique_key": "TEST-003"},
            {"unique_key": "TEST-004"},
        ]
        final_page = [
            {"unique_key": "TEST-005"},
        ]
        mock_fetch.side_effect = [
            first_page,
            second_page,
            final_page,
        ]

        result = fetch_complaint_pages(
            page_size=2,
            max_pages=5,
            bbl="2037710066",
        )

        self.assertEqual(
            result,
            first_page + second_page + final_page,
        )
        self.assertEqual(
            mock_fetch.call_args_list,
            [
                call(
                    limit=2,
                    bbl="2037710066",
                    offset=0,
                ),
                call(
                    limit=2,
                    bbl="2037710066",
                    offset=2,
                ),
                call(
                    limit=2,
                    bbl="2037710066",
                    offset=4,
                ),
            ],
        )

    @patch("src.civicbridge.nyc311_client.fetch_complaints")
    def test_stops_at_maximum_page_count(self, mock_fetch):
        mock_fetch.side_effect = [
            [
                {"unique_key": "TEST-001"},
                {"unique_key": "TEST-002"},
            ],
            [
                {"unique_key": "TEST-003"},
                {"unique_key": "TEST-004"},
            ],
        ]

        result = fetch_complaint_pages(
            page_size=2,
            max_pages=2,
        )

        self.assertEqual(len(result), 4)
        self.assertEqual(mock_fetch.call_count, 2)
        self.assertEqual(
            mock_fetch.call_args_list,
            [
                call(limit=2, bbl=None, offset=0),
                call(limit=2, bbl=None, offset=2),
            ],
        )

    @patch("src.civicbridge.nyc311_client.fetch_complaints")
    def test_rejects_invalid_page_bounds_before_fetch(
        self,
        mock_fetch,
    ):
        for page_size in (0, -1):
            with self.subTest(page_size=page_size):
                with self.assertRaisesRegex(
                    ValueError,
                    "Page size must be greater than zero",
                ):
                    fetch_complaint_pages(
                        page_size=page_size,
                    )

        for max_pages in (0, -1):
            with self.subTest(max_pages=max_pages):
                with self.assertRaisesRegex(
                    ValueError,
                    "Max pages must be greater than zero",
                ):
                    fetch_complaint_pages(
                        max_pages=max_pages,
                    )

        mock_fetch.assert_not_called()
