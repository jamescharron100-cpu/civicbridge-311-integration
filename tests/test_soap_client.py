import xml.etree.ElementTree as ET
from datetime import datetime
from unittest import TestCase

from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.soap_client import (CIVICBRIDGE_NS, SOAP_NS, build_soap_envelope)


class SoapClientTests(TestCase):
    def test_builds_soap_envelope(self):
        request = MaintenanceRequest(
            external_id="TEST-001",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16),
            source_updated_at=datetime(2026, 9, 16)
        )

        xml_bytes = build_soap_envelope(request)
        root = ET.fromstring(xml_bytes)

        self.assertIsInstance(xml_bytes, bytes)
        self.assertEqual(root.tag, f"{{{SOAP_NS}}}Envelope")

        body = root.find(f"{{{SOAP_NS}}}Body")
        self.assertIsNotNone(body)

        assert body is not None
        operation = body.find(f"{{{CIVICBRIDGE_NS}}}UpsertMaintenanceRequest")
        self.assertIsNotNone(operation)

        assert operation is not None
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}ExternalId"), request.external_id)
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}PropertyId"), request.property_id)
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}Category"), request.category)
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}Priority"), request.priority)
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}Status"), request.status)
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}Description"), request.description)

        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}ReportedAt"), request.reported_at.isoformat())
        self.assertEqual(operation.findtext(f"{{{CIVICBRIDGE_NS}}}SourceUpdatedAt"), request.source_updated_at.isoformat())
