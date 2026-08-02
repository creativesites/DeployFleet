{
    "name": "DeployFleet Driver",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Driver profile: license class, endorsements, vehicle-type qualifications, experience, risk score",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["hr", "deployfleet_core", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
    ],
}
