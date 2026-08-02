{
    "name": "DeployFleet Vehicle",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Vehicle operational profile — delegates Odoo's native fleet.vehicle rather than reinventing it",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["fleet", "hr", "deployfleet_core", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_vehicle_views.xml",
    ],
}
