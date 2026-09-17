import requests
import xml.etree.ElementTree as ET

from .models import MaintenanceRequest

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CIVICBRIDGE_NS = "urn:civicbridge:maintenance"

ET.register_namespace("soap", SOAP_NS)
ET.register_namespace("cb", CIVICBRIDGE_NS)


def build_soap_envelope(request: MaintenanceRequest) -> bytes:
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    operation = ET.SubElement(body, f"{{{CIVICBRIDGE_NS}}}UpsertMaintenanceRequest")

    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}ExternalId").text = request.external_id
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}PropertyId").text = request.property_id
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}Category").text = request.category
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}Priority").text = request.priority
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}Status").text = request.status
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}Description").text = request.description

    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}ReportedAt").text = request.reported_at.isoformat()
    ET.SubElement(operation, f"{{{CIVICBRIDGE_NS}}}SourceUpdatedAt").text = request.source_updated_at.isoformat()

    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def parse_soap_response(xml_bytes: bytes) -> str:
    root = ET.fromstring(xml_bytes)
    if root.tag != f"{{{SOAP_NS}}}Envelope":
        raise ValueError("Response is not a SOAP envelope")

    body = root.find(f"{{{SOAP_NS}}}Body")
    if body is None:
        raise ValueError("SOAP response is missing its Body")

    fault = body.find(f"{{{SOAP_NS}}}Fault")
    if fault is not None:
        raise ValueError(fault.findtext("faultstring") or "Unknown SOAP fault")

    response = body.find(f"{{{CIVICBRIDGE_NS}}}UpsertMaintenanceRequestResponse")
    if response is None:
        raise ValueError("Operation response is missing")

    result = response.findtext(f"{{{CIVICBRIDGE_NS}}}Result")
    if result not in ("CREATED", "UPDATED"):
        raise ValueError(f"Unexpected result: {result}")

    return result


def send_maintenance_request(request: MaintenanceRequest, endpoint_url: str) -> str:
    xml_bytes = build_soap_envelope(request)

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"urn:civicbridge:maintenance:UpsertMaintenanceRequest"'
    }

    response = requests.post(endpoint_url, data=xml_bytes, headers=headers, timeout=10)

    result = parse_soap_response(response.content)
    response.raise_for_status()

    return result
