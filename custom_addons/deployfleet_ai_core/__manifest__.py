{
    "name": "DeployFleet AI Core",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "AI provider router, cost/cache architecture, and company AI policy",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_core", "deployfleet_event_bus", "web"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_ai_policy_data.xml",
        "data/deployfleet_ai_config_data.xml",
        "data/deployfleet_ai_entity_summary_event_subscriptions.xml",
        "views/deployfleet_ai_views.xml",
    ],
}
