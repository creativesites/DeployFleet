{
    "name": "DeployFleet ZRA Smart Invoice",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Submits posted invoices to the Zambia Revenue Authority's Smart Invoice (VSDC) system",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_accounting", "deployfleet_security"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_zra_config_data.xml",
        "data/deployfleet_zra_event_subscriptions.xml",
        "views/deployfleet_zra_views.xml",
    ],
}
