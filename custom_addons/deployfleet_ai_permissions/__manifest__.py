{
    "name": "DeployFleet AI Permissions",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Per-role AI feature access control - the new subsystem per docs/architecture/08-ai-architecture.md §9",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_ai_core", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "views/deployfleet_ai_permission_views.xml",
    ],
}
