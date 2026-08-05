{
    "name": "DeployFleet Parts",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Parts categories, items, and low-stock alerts consumed by workshop/tyres",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_vehicle", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_parts_company_rules.xml",
        "views/deployfleet_part_views.xml",
    ],
}
