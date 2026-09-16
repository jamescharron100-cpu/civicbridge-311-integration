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