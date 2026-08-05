{
    "name": "DeployFleet Loans",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Employee loans with automatic payslip deductions",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_payroll", "deployfleet_security"],
    "data": [
        "security/ir.model.access.csv",
        "security/deployfleet_loans_company_rules.xml",
        "data/deployfleet_loan_payroll_rule.xml",
        "views/deployfleet_loan_views.xml",
    ],
}
