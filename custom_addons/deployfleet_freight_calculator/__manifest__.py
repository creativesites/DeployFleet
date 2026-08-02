{
    "name": "DeployFleet Freight Calculator",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Company-configurable cost/profit calculation engine and trucking calculators",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_vehicle", "deployfleet_route", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "data/deployfleet_calculation_rule_data.xml",
        "data/deployfleet_calculation_parameter_data.xml",
        "views/deployfleet_calculation_rule_views.xml",
        "views/deployfleet_freight_calculator_wizard_views.xml",
    ],
}
