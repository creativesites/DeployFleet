from odoo import fields, models


class DeployfleetDepot(models.Model):
    """A depot/terminal — a named origin/destination point for routes and
    shipments. Kept deliberately simple for Phase 1 (name + address text);
    link to a full res.partner record later if a depot ever needs its own
    contacts/invoicing address distinct from free text.
    """

    _name = "deployfleet.depot"
    _description = "DeployFleet Depot / Terminal"
    _order = "name"

    name = fields.Char(required=True)
    street = fields.Char()
    city = fields.Char()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("name_company_unique", "UNIQUE(name, company_id)", "A depot with this name already exists for this company."),
    ]
