{
    "name": "DeployFleet Accounting",
    "version": "19.0.1.0.0",
    "category": "DeployFleet",
    "summary": "Posts confirmed DeployFleet invoices as real Odoo accounting entries",
    "author": "DeployFleet",
    "license": "LGPL-3",
    "depends": ["deployfleet_billing", "account", "deployfleet_security"],
    "data": [
        "data/deployfleet_accounting_product_data.xml",
        "views/deployfleet_invoice_views.xml",
    ],
}
