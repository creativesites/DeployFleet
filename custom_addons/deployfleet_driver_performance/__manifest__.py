{
    "name": "DeployFleet Driver Performance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Driver safety/performance events -> reliability score, optional payroll deduction",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_loans", "deployfleet_driver", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_driver_performance_payroll_rule.xml",
        "views/deployfleet_driver_performance_event_views.xml",
    ],
}
