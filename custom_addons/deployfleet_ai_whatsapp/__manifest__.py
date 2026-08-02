{
    "name": "DeployFleet AI WhatsApp",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Action-capable WhatsApp channel - inbound reports become AI action requests, never auto-executed",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_ai_actions", "deployfleet_vehicle", "deployfleet_driver"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_ai_whatsapp_feature_data.xml",
        "views/deployfleet_ai_whatsapp_config_views.xml",
    ],
}
