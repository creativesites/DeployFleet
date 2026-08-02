{
    "name": "DeployFleet Security",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Role groups and product license/entitlement enforcement for DeployFleet",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_core", "hr", "base", "web"],
    "data": [
        "security/deployfleet_security_groups.xml",
        "security/ir.model.access.csv",
        "views/deployfleet_license_views.xml",
        "views/res_config_settings_views.xml",
        "data/deployfleet_license_cron.xml",
    ],
}
