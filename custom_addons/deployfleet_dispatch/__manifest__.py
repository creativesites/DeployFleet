{
    "name": "DeployFleet Dispatch",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Shipments and dispatch assignments — scoring-based driver/vehicle matching",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": [
        "deployfleet_customer", "deployfleet_route", "deployfleet_vehicle",
        "deployfleet_driver", "deployfleet_event_bus", "deployfleet_security",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_dispatch_company_rules.xml",
        "data/deployfleet_shipment_sequence.xml",
        "views/deployfleet_shipment_views.xml",
        "views/deployfleet_dispatch_assignment_views.xml",
    ],
}
