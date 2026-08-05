{
    "name": "DeployFleet Driver Performance",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Driver safety/performance events -> reliability score, optional payroll deduction",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_loans", "deployfleet_driver", "mail", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_driver_performance_company_rules.xml",
        "data/deployfleet_driver_performance_payroll_rule.xml",
        "views/deployfleet_driver_performance_event_views.xml",
    ],
}
