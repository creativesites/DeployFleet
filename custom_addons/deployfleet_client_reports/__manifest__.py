{
    "name": "DeployFleet Client Reports",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Per-customer PDF summary of shipments, on-time performance, and billing over a date range",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_billing", "deployfleet_delivery", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_client_report_wizard_views.xml",
        "report/deployfleet_client_report_templates.xml",
    ],
}
