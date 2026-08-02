from odoo import fields, models


class DeployfleetLeaveBalance(models.Model):
    """One employee's leave allocation for one leave type in one year."""

    _name = "deployfleet.leave.balance"
    _description = "DeployFleet Leave Balance"
    _order = "year desc"

    employee_id = fields.Many2one("hr.employee", required=True)
    leave_type_id = fields.Many2one("deployfleet.leave.type", required=True)
    year = fields.Integer(required=True, default=lambda self: fields.Date.today().year)
    allocated_days = fields.Float()
    used_days = fields.Float(compute="_compute_used_days")
    remaining_days = fields.Float(compute="_compute_used_days")

    _sql_constraints = [
        ("employee_type_year_unique", "UNIQUE(employee_id, leave_type_id, year)",
         "A leave balance for this employee/type/year already exists."),
    ]

    def _compute_used_days(self):
        # Not stored, and deliberately not @api.depends-tracked: used_days
        # is derived from deployfleet.leave.request records that have no
        # direct FK back to this model (matched only by
        # employee/type/year), so Odoo's automatic dependency tracking
        # can't fire when a request's state changes. Computing fresh on
        # every read is simpler and correct; there's no dispatch-blocking
        # logic relying on this being indexable/searchable.
        request_model = self.env["deployfleet.leave.request"]
        for balance in self:
            requests = request_model.search([
                ("employee_id", "=", balance.employee_id.id),
                ("leave_type_id", "=", balance.leave_type_id.id),
                ("state", "=", "approved"),
                ("date_from", ">=", f"{balance.year}-01-01"),
                ("date_from", "<=", f"{balance.year}-12-31"),
            ])
            balance.used_days = sum(requests.mapped("number_of_days"))
            balance.remaining_days = balance.allocated_days - balance.used_days
