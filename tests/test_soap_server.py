from datetime import datetime
from unittest import TestCase
from threading import Thread


from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.soap_client import build_soap_envelope, parse_soap_response, send_maintenance_request
from src.civicbridge.soap_server import parse_maintenance_request, build_soap_response, build_soap_fault, upsert_maintenance_request, SoapHTTPServer, SoapRequestHandler


class SoapServerTests(TestCase):
    def test_parses_maintenance_request(self):
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

        fields = parse_maintenance_request(build_soap_envelope(request))

        self.assertEqual(
            fields,
            {
                "ExternalId": "TEST-001",
                "PropertyId": "CB-001",
                "Category": "HEATING",
                "Priority": "HIGH",
                "Status": "OPEN",
                "Description": "Heat & hot water",
                "ReportedAt": "2026-09-16T00:00:00",
                "SourceUpdatedAt": "2026-09-16T00:00:00",
            },
        )

    def test_rejects_missing_required_field(self):
        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <cb:UpsertMaintenanceRequest>
                    <cb:ExternalId>TEST-002</cb:ExternalId>
                </cb:UpsertMaintenanceRequest>
            </soap:Body>
        </soap:Envelope>
        """

        with self.assertRaisesRegex(
            ValueError, "Missing required field: PropertyId"
        ):
            parse_maintenance_request(xml_bytes)


    def test_builds_created_response(self):
        xml_bytes = build_soap_response("TEST-001", "CREATED")

        self.assertIsInstance(xml_bytes, bytes)
        self.assertEqual(parse_soap_response(xml_bytes), "CREATED")


    def test_builds_soap_fault(self):
        xml_bytes = build_soap_fault("Unknown property ID")

        self.assertIsInstance(xml_bytes, bytes)
        with self.assertRaisesRegex(ValueError, "Unknown property ID"):
            parse_soap_response(xml_bytes)


    def test_creates_and_updates_maintenance_request(self):
        cases = {}
        fields = {
            "ExternalId": "TEST-001",
            "Description": "Heat & hot water",
        }

        result = upsert_maintenance_request(fields, cases)

        self.assertEqual(result, "CREATED")
        self.assertEqual(cases["TEST-001"], fields)

        fields["Description"] = "Updated heating complaint"
        self.assertEqual(
            cases["TEST-001"]["Description"], "Heat & hot water"
        )

        result = upsert_maintenance_request(fields, cases)

        self.assertEqual(result, "UPDATED")
        self.assertEqual(cases["TEST-001"], fields)
        self.assertEqual(len(cases), 1)


    def test_creates_and_updates_over_http(self):
        request = MaintenanceRequest(
            external_id="HTTP-TEST-001",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16),
            source_updated_at=datetime(2026, 9, 16),
        )

        with SoapHTTPServer(("127.0.0.1", 0), SoapRequestHandler) as server:
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            endpoint = f"http://127.0.0.1:{server.server_port}/soap"

            try:
                self.assertEqual(
                    send_maintenance_request(request, endpoint), "CREATED"
                )
                self.assertEqual(
                    send_maintenance_request(request, endpoint), "UPDATED"
                )
            finally:
                server.shutdown()
                thread.join(timeout=5)

            self.assertEqual(len(server.cases), 1)
            self.assertEqual(
                server.cases["HTTP-TEST-001"]["Description"],
                "Heat & hot water",
            )