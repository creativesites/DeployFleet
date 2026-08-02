{
    "name": "DeployFleet Notifications",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Data-driven event-bus subscriber that turns operational events into notifications",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_delivery", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_notification_rule_data.xml",
        "views/deployfleet_notification_views.xml",
    ],
}
