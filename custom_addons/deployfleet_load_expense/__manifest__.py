{
    "name": "DeployFleet Load Expense",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Actual costs incurred per shipment/trip — fuel, tolls, fees, permits",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_dispatch", "deployfleet_trip", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_load_expense_company_rules.xml",
        "views/deployfleet_load_expense_views.xml",
    ],
}
