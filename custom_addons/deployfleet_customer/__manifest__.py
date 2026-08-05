{
    "name": "DeployFleet Customer",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Customer contracts and depots/terminals",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["contacts", "deployfleet_core", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_customer_company_rules.xml",
        "data/deployfleet_contract_sequence.xml",
        "views/deployfleet_contract_views.xml",
        "views/deployfleet_depot_views.xml",
    ],
}
