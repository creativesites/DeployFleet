{
    "name": "DeployFleet Leave",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Leave types, balances, and requests — blocks approval against scheduled trips",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_trip", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_leave_type_data.xml",
        "views/deployfleet_leave_request_views.xml",
    ],
}
