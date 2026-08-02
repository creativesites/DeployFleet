from odoo import api, fields, models


class DeployfleetLoan(models.Model):
    """An employee loan, deducted from payslips via
    deployfleet_payroll_payslip.py's action_compute()/action_confirm()
    extensions in this module. See docs/architecture/04-module-structure.md:
    'Employee loans, payslip deductions.'
    """

    _name = "deployfleet.loan"
    _description = "DeployFleet Employee Loan"
    _order = "start_date desc"

    employee_id = fields.Many2one("hr.employee", required=True)
    amount = fields.Monetary(required=True)
    monthly_deduction = fields.Monetary(required=True)
    start_date = fields.Date(required=True, default=fields.Date.context_today)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    outstanding_balance = fields.Monetary()
    state = fields.Selection([("active", "Active"), ("closed", "Closed")], default="active", required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "outstanding_balance" not in vals:
                vals["outstanding_balance"] = vals.get("amount", 0.0)
        return super().create(vals_list)

    def _deduction_for_payslip(self):
        self.ensure_one()
        return min(self.monthly_deduction, self.outstanding_balance)

    def action_apply_deduction(self, amount):
        self.ensure_one()
        self.outstanding_balance = max(0.0, self.outstanding_balance - amount)
        if self.outstanding_balance == 0.0:
            self.state = "closed"
