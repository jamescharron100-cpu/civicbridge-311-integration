from datetime import datetime, timezone
from unittest import TestCase

from src.civicbridge.matcher import find_matching_property
from src.civicbridge.models import Complaint
from src.civicbridge.properties import PROPERTIES


class MatcherTests(TestCase):
    def test_matches_by_bbl(self):
        complaint = Complaint(
            source_id="TEST-001",
            created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="HEAT/HOT WATER",
            status="Open",
            source_updated_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            bbl="2037710066",
        )

        match = find_matching_property(complaint, PROPERTIES)

        self.assertEqual(match, PROPERTIES[0])

    def test_matches_by_normalized_address_and_borough(self):
        complaint = Complaint(
            source_id="TEST-002",
            created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="HEAT/HOT WATER",
            status="Open",
            source_updated_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            incident_address="  606 West   141 Street ",
            borough="manhattan",
        )

        match = find_matching_property(complaint, PROPERTIES)

        self.assertEqual(match, PROPERTIES[1])

    def test_returns_none_when_no_property_matches(self):
        complaint = Complaint(
            source_id="TEST-003",
            created_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="HEAT/HOT WATER",
            status="Open",
            source_updated_at=datetime(2026, 9, 15, tzinfo=timezone.utc),
            incident_address="999 NOWHERE STREET",
            borough="QUEENS",
            bbl="9999999999",
        )

        match = find_matching_property(complaint, PROPERTIES)

        self.assertIsNone(match)
