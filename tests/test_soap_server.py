import sqlite3
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from unittest import TestCase

from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.soap_client import (
    build_soap_envelope,
    parse_soap_response,
    send_maintenance_request,
)
from src.civicbridge.soap_server import (
    SoapHTTPServer,
    SoapRequestHandler,
    build_soap_fault,
    build_soap_response,
    parse_maintenance_request,
)


class SoapServerTests(TestCase):
    def test_parses_maintenance_request(self):
        request = MaintenanceRequest(
            external_id="TEST-001",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc)
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
                "ReportedAt": "2026-09-16T00:00:00+00:00",
                "SourceUpdatedAt": "2026-09-16T00:00:00+00:00",
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


    def test_persists_case_across_server_restart(self):
        request = MaintenanceRequest(
            external_id="HTTP-TEST-001",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
            source_updated_at=datetime(2026, 9, 16, tzinfo=timezone.utc),
        )

        with TemporaryDirectory() as temp_dir:
            db_path = str(Path(temp_dir) / "cases.db")

            for expected_result in ("CREATED", "UPDATED"):
                with SoapHTTPServer(
                    ("127.0.0.1", 0),
                    SoapRequestHandler,
                    db_path,
                ) as server:
                    thread = Thread(
                        target=server.serve_forever,
                        daemon=True,
                    )
                    thread.start()
                    endpoint = (
                        f"http://127.0.0.1:{server.server_port}/soap"
                    )

                    try:
                        self.assertEqual(
                            send_maintenance_request(request, endpoint),
                            expected_result,
                        )
                    finally:
                        server.shutdown()
                        thread.join(timeout=5)

                request = replace(
                    request,
                    description="Updated heating complaint",
                    source_updated_at=datetime(2026, 9, 18, tzinfo=timezone.utc),
                )

            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    """
                    SELECT external_id, description, source_updated_at
                    FROM maintenance_cases
                    """
                ).fetchall()
            finally:
                conn.close()

            self.assertEqual(
                rows,
                [
                    (
                        "HTTP-TEST-001",
                        "Updated heating complaint",
                        "2026-09-18T00:00:00+00:00",
                    )
                ],
            )
