from .models import Property


PROPERTIES: list[Property] = [
    Property(
        property_id="CB-001",
        name="Wheeler Avenue Property",
        address="1227 WHEELER AVENUE",
        borough="BRONX",
        bbl="2037710066",
    ),
    Property(
        property_id="CB-002",
        name="West 141st Street Property",
        address="606 WEST 141 STREET",
        borough="MANHATTAN",
    ),
]
