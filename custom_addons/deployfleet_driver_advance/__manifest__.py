{
    "name": "DeployFleet Driver Advance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Cash advances to drivers for fuel float, tolls/border fees, subsistence",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_driver", "deployfleet_trip", "deployfleet_load_expense", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_driver_advance_views.xml",
    ],
}
