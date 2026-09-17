import xml.etree.ElementTree as ET
from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock, patch

from src.civicbridge.models import MaintenanceRequest
from src.civicbridge.soap_client import (CIVICBRIDGE_NS, SOAP_NS, build_soap_envelope, parse_soap_response, send_maintenance_request)


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


    def test_parses_created_response(self):
        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <cb:UpsertMaintenanceRequestResponse>
                    <cb:ExternalId>TEST-001</cb:ExternalId>
                    <cb:Result>CREATED</cb:Result>
                </cb:UpsertMaintenanceRequestResponse>
            </soap:Body>
        </soap:Envelope>
        """

        self.assertEqual(parse_soap_response(xml_bytes), "CREATED")


    def test_parses_updated_response(self):
        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <cb:UpsertMaintenanceRequestResponse>
                    <cb:ExternalId>TEST-001</cb:ExternalId>
                    <cb:Result>UPDATED</cb:Result>
                </cb:UpsertMaintenanceRequestResponse>
            </soap:Body>
        </soap:Envelope>
        """

        self.assertEqual(parse_soap_response(xml_bytes), "UPDATED")


    def test_raises_for_soap_fault(self):
        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <soap:Fault>
                    <faultcode>soap:Client</faultcode>
                    <faultstring>Unknown property ID</faultstring>
                </soap:Fault>
            </soap:Body>
        </soap:Envelope>
        """

        with self.assertRaisesRegex(ValueError, "Unknown property ID"):
            parse_soap_response(xml_bytes)


    def test_rejects_unexpected_result(self):
        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <cb:UpsertMaintenanceRequestResponse>
                    <cb:ExternalId>TEST-001</cb:ExternalId>
                    <cb:Result>PENDING</cb:Result>
                </cb:UpsertMaintenanceRequestResponse>
            </soap:Body>
        </soap:Envelope>
        """

        with self.assertRaisesRegex(ValueError, "Unexpected result: PENDING"):
            parse_soap_response(xml_bytes)


    def test_sends_maintenance_request(self):
        request = MaintenanceRequest(
            external_id="TEST-002",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16),
            source_updated_at=datetime(2026, 9, 16)
        )

        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                       xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <cb:UpsertMaintenanceRequestResponse>
                    <cb:ExternalId>TEST-001</cb:ExternalId>
                    <cb:Result>CREATED</cb:Result>
                </cb:UpsertMaintenanceRequestResponse>
            </soap:Body>
        </soap:Envelope>
        """

        mock_response = Mock()
        mock_response.content = xml_bytes

        with patch(
            "src.civicbridge.soap_client.requests.post",
            return_value=mock_response,
        ) as mock_post:
            result = send_maintenance_request(
                request, "http://localhost:8000/soap"
            )

        self.assertEqual(result, "CREATED")

        mock_post.assert_called_once_with(
            "http://localhost:8000/soap",
            data=build_soap_envelope(request),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": '"urn:civicbridge:maintenance:UpsertMaintenanceRequest"',
            },
            timeout=10,
        )
        mock_response.raise_for_status.assert_called_once_with()


    def test_send_raises_for_soap_fault(self):
        request = MaintenanceRequest(
            external_id="TEST-003",
            property_id="CB-001",
            category="HEATING",
            priority="HIGH",
            status="OPEN",
            description="Heat & hot water",
            reported_at=datetime(2026, 9, 16),
            source_updated_at=datetime(2026, 9, 16)
        )

        xml_bytes = b"""
        <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
                        xmlns:cb="urn:civicbridge:maintenance">
            <soap:Body>
                <soap:Fault>
                    <faultcode>soap:Client</faultcode>
                    <faultstring>Unknown property ID</faultstring>
                </soap:Fault>
            </soap:Body>
        </soap:Envelope>
        """

        mock_response = Mock()
        mock_response.content = xml_bytes

        with patch(
            "src.civicbridge.soap_client.requests.post",
            return_value=mock_response,
        ):
            with self.assertRaisesRegex(ValueError, "Unknown property ID"):
                send_maintenance_request(
                    request, "http://localhost:8000/soap"
                )

        mock_response.raise_for_status.assert_not_called()
