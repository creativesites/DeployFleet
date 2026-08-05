{
    "name": "DeployFleet Dispatch Compliance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Blocks dispatch against expired documents, rest-hour and leave conflicts, with emergency override",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": [
        "deployfleet_compliance", "deployfleet_dispatch", "deployfleet_trip", "deployfleet_leave",
        "deployfleet_security",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_dispatch_compliance_company_rules.xml",
        "data/deployfleet_driver_compliance_document_types.xml",
        "views/deployfleet_dispatch_assignment_views.xml",
    ],
}
