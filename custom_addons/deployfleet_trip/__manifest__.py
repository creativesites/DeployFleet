{
    "name": "DeployFleet Trip",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Trip execution: planned vs. actual, created automatically when a dispatch assignment is confirmed",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_dispatch", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_trip_security_rules.xml",
        "data/deployfleet_trip_sequence.xml",
        "data/deployfleet_trip_event_subscriptions.xml",
        "views/deployfleet_trip_views.xml",
    ],
}
