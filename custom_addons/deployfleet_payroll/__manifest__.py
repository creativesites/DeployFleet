{
    "name": "DeployFleet Payroll",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Country-neutral payroll rule engine and payslips",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_core", "deployfleet_leave", "web", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_payroll_company_rules.xml",
        "views/deployfleet_payroll_payslip_views.xml",
    ],
}
