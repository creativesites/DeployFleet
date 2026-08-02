{
    "name": "DeployFleet Compliance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Polymorphic document/expiry engine shared by driver and vehicle compliance",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_core", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_compliance_cron.xml",
        "views/deployfleet_compliance_document_views.xml",
    ],
}
