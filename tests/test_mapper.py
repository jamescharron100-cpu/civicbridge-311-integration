from datetime import datetime, timezone
from unittest import TestCase

from src.civicbridge.mapper import map_complaint
from src.civicbridge.models import Complaint
from src.civicbridge.properties import PROPERTIES


class MapperTests(TestCase):
    def test_maps_heat_complaint(self):
        complaint = Complaint(
            source_id="TEST-001",
            created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="HEAT/HOT WATER",
            status="Open",
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            descriptor="ENTIRE BUILDING"
        )

        request = map_complaint(complaint, PROPERTIES[0])

        self.assertEqual(request.external_id, "TEST-001")
        self.assertEqual(request.property_id, "CB-001")
        self.assertEqual(request.category, "HEATING")
        self.assertEqual(request.priority, "HIGH")
        self.assertEqual(request.status, "OPEN")
        self.assertEqual(request.description, "HEAT/HOT WATER: ENTIRE BUILDING")
        self.assertEqual(request.reported_at, complaint.created_at)
        self.assertEqual(request.source_updated_at, complaint.source_updated_at)


    def test_maps_complaint_without_descriptor(self):
        complaint = Complaint(
            source_id="TEST-002",
            created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="PLUMBING",
            status="Open",
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

        request = map_complaint(complaint, PROPERTIES[0])

        self.assertEqual(request.external_id, "TEST-002")
        self.assertEqual(request.property_id, "CB-001")
        self.assertEqual(request.category, "PLUMBING")
        self.assertEqual(request.priority, "NORMAL")
        self.assertEqual(request.status, "OPEN")
        self.assertEqual(request.description, "PLUMBING")
        self.assertEqual(request.reported_at, complaint.created_at)
        self.assertEqual(request.source_updated_at, complaint.source_updated_at)


    def test_maps_closed_elevator_complaint(self):
        complaint = Complaint(
            source_id="TEST-003",
            created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="ELEVATOR",
            status="Closed",
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

        request = map_complaint(complaint, PROPERTIES[0])

        self.assertEqual(request.external_id, "TEST-003")
        self.assertEqual(request.property_id, "CB-001")
        self.assertEqual(request.category, "ELEVATOR")
        self.assertEqual(request.priority, "HIGH")
        self.assertEqual(request.status, "CLOSED")
        self.assertEqual(request.description, "ELEVATOR")
        self.assertEqual(request.reported_at, complaint.created_at)
        self.assertEqual(request.source_updated_at, complaint.source_updated_at)


    def test_rejects_unsupported_complaint_type(self):
        complaint = Complaint(
            source_id="TEST-004",
            created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="NOISE",
            status="Open",
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

        with self.assertRaises(ValueError):
            map_complaint(complaint, PROPERTIES[0])


    def test_rejects_unsupported_status(self):
        complaint = Complaint(
            source_id="TEST-005",
            created_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            agency="HPD",
            complaint_type="PLUMBING",
            status="Pending",
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

        with self.assertRaises(ValueError):
            map_complaint(complaint, PROPERTIES[0])
