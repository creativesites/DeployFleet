from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetDriverAdvance(models.Model):
    """A cash advance issued to a driver for fuel float, tolls/border fees,
    or subsistence on a trip — see
    docs/architecture/15-load-sheet-architecture.md §6, flagged there as
    the strongest standalone idea in the load-sheet proposal it
    reconciles: a real, underserved operational need for African
    long-haul trucking.

    Reconciles against `deployfleet.load.expense` records (added via
    `advance_id` in this module, see deployfleet_load_expense.py) and,
    once `deployfleet_payroll` exists (Phase 3), an unreconciled balance
    can feed that module's deduction pipeline — the same mechanism
    `deployfleet_loans` will use, not a second one.
    """

    _name = "deployfleet.driver.advance"
    _description = "DeployFleet Driver Cash Advance"
    _order = "issued_date desc"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    driver_id = fields.Many2one("hr.employee", required=True, domain=[("deployfleet_is_driver", "=", True)])
    trip_id = fields.Many2one("deployfleet.trip")
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    issued_date = fields.Date(default=fields.Date.context_today, required=True)
    purpose = fields.Selection(
        [
            ("fuel", "Fuel Float"),
            ("toll_border", "Tolls/Border Fees"),
            ("subsistence", "Subsistence"),
            ("other", "Other"),
        ],
        required=True, default="fuel",
    )
    reconciled_expense_ids = fields.One2many(
        "deployfleet.load.expense", "advance_id", string="Reconciled Expenses",
        help="Actual expenses this advance was meant to cover.",
    )
    reconciled_amount = fields.Monetary(compute="_compute_reconciled_amount", store=True)
    outstanding_amount = fields.Monetary(compute="_compute_reconciled_amount", store=True)
    state = fields.Selection(
        [
            ("issued", "Issued"),
            ("reconciled", "Reconciled"),
            ("deducted", "Deducted from Payroll"),
        ],
        default="issued", required=True,
    )

    @api.depends("amount", "reconciled_expense_ids.amount")
    def _compute_reconciled_amount(self):
        for advance in self:
            advance.reconciled_amount = sum(advance.reconciled_expense_ids.mapped("amount"))
            advance.outstanding_amount = advance.amount - advance.reconciled_amount

    def action_mark_reconciled(self):
        for advance in self:
            if advance.state != "issued":
                raise UserError(self.env._("Only an issued advance can be marked reconciled."))
            advance.state = "reconciled"

    def action_mark_deducted(self):
        for advance in self:
            if advance.state != "reconciled":
                raise UserError(self.env._("Only a reconciled advance can be marked deducted from payroll."))
            advance.state = "deducted"
