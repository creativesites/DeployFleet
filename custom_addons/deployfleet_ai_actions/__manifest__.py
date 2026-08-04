{
    "name": "DeployFleet AI Actions",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "The suggestion -> approval -> execute -> audit pipeline for AI-initiated writes",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_ai_permissions", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_ai_action_sequence.xml",
        "data/deployfleet_ai_auto_executable_action_data.xml",
        "views/deployfleet_ai_action_request_views.xml",
    ],
}
