{
    "name": "DeployFleet Fuel",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Fuel logs, consumption analytics, and simple threshold anomaly flags",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_vehicle", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_fuel_company_rules.xml",
        "views/deployfleet_fuel_log_views.xml",
    ],
}
