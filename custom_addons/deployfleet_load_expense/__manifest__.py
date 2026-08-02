{
    "name": "DeployFleet Load Expense",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Actual costs incurred per shipment/trip — fuel, tolls, fees, permits",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_dispatch", "deployfleet_trip"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_load_expense_views.xml",
    ],
}
