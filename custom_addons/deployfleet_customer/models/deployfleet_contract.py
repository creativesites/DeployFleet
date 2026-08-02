from odoo import api, fields, models


class DeployfleetContract(models.Model):
    """Recurring commercial terms with a customer. Deliberately optional on
    a shipment (docs/architecture/07-domain-model-erd.md §3) — a shipment
    with no contract is a spot load, not an error state.
    """

    _name = "deployfleet.contract"
    _description = "DeployFleet Customer Contract"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    customer_id = fields.Many2one("res.partner", required=True)
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    rate_basis = fields.Selection(
        [
            ("per_trip", "Per Trip"),
            ("per_tonnage", "Per Tonnage"),
            ("per_distance", "Per Distance"),
            ("per_lane", "Per Lane"),
        ],
        required=True,
        default="per_trip",
    )
    start_date = fields.Date(required=True, default=fields.Date.today)
    end_date = fields.Date()
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("expired", "Expired"), ("terminated", "Terminated")],
        default="draft",
        required=True,
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.contract")
        return super().create(vals_list)

    def action_activate(self):
        self.write({"state": "active"})

    def action_terminate(self):
        self.write({"state": "terminated"})

    @api.model
    def _cron_expire_contracts(self):
        today = fields.Date.today()
        expiring = self.search([("state", "=", "active"), ("end_date", "!=", False), ("end_date", "<", today)])
        expiring.write({"state": "expired"})
        return expiring
