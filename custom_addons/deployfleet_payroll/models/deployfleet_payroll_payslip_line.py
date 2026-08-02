from odoo import fields, models


class DeployfleetPayrollPayslipLine(models.Model):
    _name = "deployfleet.payroll.payslip.line"
    _description = "DeployFleet Payslip Line"
    _order = "rule_id"

    payslip_id = fields.Many2one("deployfleet.payroll.payslip", required=True, ondelete="cascade")
    rule_id = fields.Many2one("deployfleet.payroll.rule", required=True)
    amount = fields.Monetary()
    currency_id = fields.Many2one(related="payslip_id.currency_id", store=True)
