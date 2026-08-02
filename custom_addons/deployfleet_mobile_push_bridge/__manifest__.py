{
    "name": "DeployFleet Mobile Push Bridge",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Device token registration and push notifications (Expo) wired to the event bus",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_delivery", "deployfleet_core", "deployfleet_security"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/deployfleet_mobile_device_security.xml",
        "security/ir.model.access.csv",
        "data/deployfleet_mobile_push_bridge_event_subscriptions.xml",
        "views/deployfleet_mobile_device_views.xml",
    ],
}
