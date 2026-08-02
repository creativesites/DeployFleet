{
    "name": "DeployFleet Customer Portal",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Customer-facing portal: shipment status, active trips, proof of delivery, invoices",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["portal", "deployfleet_delivery", "deployfleet_billing", "deployfleet_security"],
    "data": [
        "security/deployfleet_customer_portal_security.xml",
        "security/ir.model.access.csv",
        "views/deployfleet_portal_templates.xml",
    ],
}
