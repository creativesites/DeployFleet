{
    "name": "DeployFleet Billing",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Rate cards and billable invoices generated automatically from completed trips",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_trip", "deployfleet_customer", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_invoice_sequence.xml",
        "data/deployfleet_billing_event_subscriptions.xml",
        "views/deployfleet_rate_card_views.xml",
        "views/deployfleet_invoice_views.xml",
    ],
}
