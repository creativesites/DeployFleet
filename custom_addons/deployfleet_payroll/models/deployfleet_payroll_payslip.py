from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetPayrollPayslip(models.Model):
    """One employee's payslip for one period — runs every active
    deployfleet.payroll.rule in sequence, threading each rule's computed
    amount into the context available to later rules (so a percentage
    or formula rule can reference an earlier one by code)."""

    _name = "deployfleet.payroll.payslip"
    _description = "DeployFleet Payslip"
    _order = "period_start desc"

    employee_id = fields.Many2one("hr.employee", required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many("deployfleet.payroll.payslip.line", "payslip_id")
    gross_pay = fields.Monetary(compute="_compute_pay_totals", store=True)
    total_deductions = fields.Monetary(compute="_compute_pay_totals", store=True)
    net_pay = fields.Monetary(compute="_compute_pay_totals", store=True)
    state = fields.Selection(
        [("draft", "Draft"), ("computed", "Computed"), ("confirmed", "Confirmed"), ("paid", "Paid")],
        default="draft", required=True,
    )

    @api.depends("line_ids.amount", "line_ids.rule_id.category")
    def _compute_pay_totals(self):
        for payslip in self:
            payslip.gross_pay = sum(
                payslip.line_ids.filtered(lambda line: line.rule_id.category == "gross").mapped("amount")
            )
            payslip.total_deductions = sum(
                payslip.line_ids.filtered(lambda line: line.rule_id.category == "deduction").mapped("amount")
            )
            payslip.net_pay = payslip.gross_pay - payslip.total_deductions

    def action_compute(self):
        for payslip in self:
            if payslip.state not in ("draft", "computed"):
                raise UserError(self.env._("A confirmed or paid payslip cannot be recomputed."))
            payslip.line_ids.unlink()
            rules = self.env["deployfleet.payroll.rule"].search([("active", "=", True)])
            context_values = {}
            lines_vals = []
            for rule in rules:
                value = rule._compute_amount(context_values)
                context_values[rule.code] = value
                lines_vals.append((0, 0, {"rule_id": rule.id, "amount": value}))
            payslip.write({"line_ids": lines_vals, "state": "computed"})

    def action_confirm(self):
        for payslip in self:
            if payslip.state != "computed":
                raise UserError(self.env._("Compute the payslip before confirming it."))
            payslip.state = "confirmed"

    def action_mark_paid(self):
        for payslip in self:
            if payslip.state != "confirmed":
                raise UserError(self.env._("Confirm the payslip before marking it paid."))
            payslip.state = "paid"
