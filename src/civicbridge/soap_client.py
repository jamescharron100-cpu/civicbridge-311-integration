import time
import xml.etree.ElementTree as ET

import requests

from .models import MaintenanceRequest

SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
CIVICBRIDGE_NS = "urn:civicbridge:maintenance"
SOAP_MAX_ATTEMPTS = 3
SOAP_RETRY_BACKOFF_SECONDS = 0.25

ET.register_namespace("soap", SOAP_NS)
ET.register_namespace("cb", CIVICBRIDGE_NS)

class SoapFaultError(ValueError):
    pass


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
        raise SoapFaultError(fault.findtext("faultstring") or "Unknown SOAP fault")

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

    response = post_with_retries(endpoint_url, xml_bytes, headers)

    result = parse_soap_response(response.content)
    response.raise_for_status()

    return result


def post_with_retries(
    endpoint_url: str,
    xml_bytes: bytes,
    headers: dict[str, str],
    max_attempts: int = SOAP_MAX_ATTEMPTS,
) -> requests.Response:

    if max_attempts <= 0:
        raise ValueError("Max attempts must be greater than zero")

    for attempt_number in range(1, max_attempts + 1):
        try:
            response = requests.post(endpoint_url, data=xml_bytes, headers=headers, timeout=10)
            return response

        except (requests.Timeout, requests.ConnectionError):
            if attempt_number == max_attempts:
                raise

        time.sleep(SOAP_RETRY_BACKOFF_SECONDS * (2 ** (attempt_number - 1)))

    raise RuntimeError("SOAP retry loop exited unexpectedly")
