import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, HTTPServer

from .case_store import initialize_database, upsert_case
from .soap_client import CIVICBRIDGE_NS, SOAP_NS


def parse_maintenance_request(xml_bytes: bytes) -> dict[str, str]:
    root = ET.fromstring(xml_bytes)

    if root.tag != f"{{{SOAP_NS}}}Envelope":
        raise ValueError("Request is not a SOAP envelope")

    body = root.find(f"{{{SOAP_NS}}}Body")
    if body is None:
        raise ValueError("SOAP request is missing its Body")

    request = body.find(f"{{{CIVICBRIDGE_NS}}}UpsertMaintenanceRequest")
    if request is None:
        raise ValueError("Operation request is missing")

    field_names = ("ExternalId", "PropertyId", "Category", "Priority", "Status", "Description", "ReportedAt", "SourceUpdatedAt")
    fields = {}

    for field_name in field_names:
        value = request.findtext(f"{{{CIVICBRIDGE_NS}}}{field_name}")
        if value is None or not value.strip():
            raise ValueError(f"Missing required field: {field_name}")
        fields[field_name] = value

    return fields


def build_soap_response(external_id: str, result: str) -> bytes:
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    operation = ET.SubElement(body, f"{{{CIVICBRIDGE_NS}}}UpsertMaintenanceRequestResponse")

    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}ExternalId").text = external_id
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}Result").text = result

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def build_soap_fault(message: str) -> bytes:
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    fault = ET.SubElement(body, f"{{{SOAP_NS}}}Fault")

    ET.SubElement(fault, "faultcode").text = "soap:Client"
    ET.SubElement(fault, "faultstring").text = message

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


class SoapHTTPServer(HTTPServer):
    def __init__(self, server_address, handler_class, db_path: str):
        self.db_path = db_path
        initialize_database(self.db_path)
        super().__init__(server_address, handler_class)


class SoapRequestHandler(BaseHTTPRequestHandler):
    def send_xml_response(self, status_code: int, xml_bytes:bytes) -> None:
        self.send_response(status_code)

        self.send_header("Content-Type", "text/xml; chatset=utf-8")
        self.send_header("Content-Length", str(len(xml_bytes)))
        self.end_headers()

        self.wfile.write(xml_bytes)


    def do_POST(self) -> None:
        if self.path != "/soap":
            self.send_xml_response(404, build_soap_fault("Endpoint not found"))
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_xml_response(400, build_soap_fault("Invalid Content-Length"))
            return

        if content_length <= 0 or content_length > 1_000_000:
            self.send_xml_response(400, build_soap_fault("Request body size is invalid"))
            return

        self.connection.settimeout(10)

        try:
            xml_bytes = self.rfile.read(content_length)
        except TimeoutError:
            self.send_xml_response(408, build_soap_fault("Request body timed out"))
            return

        if len(xml_bytes) != content_length:
            self.send_xml_response(400, build_soap_fault("Incomplete request body"))
            return

        try:
            fields = parse_maintenance_request(xml_bytes)
        except (ET.ParseError, ValueError) as error:
            self.send_xml_response(500, build_soap_fault(str(error)))
            return

        assert isinstance(self.server, SoapHTTPServer)
        result = upsert_case(self.server.db_path, fields)

        self.send_xml_response(200, build_soap_response(fields["ExternalId"], result))


def run_server() -> None:
    with SoapHTTPServer(
        ("127.0.0.1", 8000),
        SoapRequestHandler,
        "civicbridge_cases.db",
    ) as server:
        print("SOAP server listening on http://127.0.0.1:8000/soap")
        server.serve_forever()


if __name__ == "__main__":
    run_server()
