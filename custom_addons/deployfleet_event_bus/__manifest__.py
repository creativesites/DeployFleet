{
    "name": "DeployFleet Event Bus",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Cross-module event publish/subscribe bus with a subscriber registry (no hardcoded consumers)",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_core", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_event_views.xml",
    ],
}
