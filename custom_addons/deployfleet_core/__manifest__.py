{
    "name": "DeployFleet Core",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "DeployFleet base module: module category, root app menu, shared foundation",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["base", "mail", "web"],
    "data": [
        "data/deployfleet_module_category.xml",
        "views/deployfleet_menus.xml",
        "security/ir.model.access.csv",
        "data/deployfleet_vehicle_type_data.xml",
        "views/deployfleet_vehicle_type_views.xml",
    ],
    "application": True,
}
