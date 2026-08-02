from odoo import models


class DeployfleetPayrollPayslip(models.Model):
    """Adds loan deductions from this module (not from deployfleet_payroll
    itself), keeping the dependency one-way — deployfleet_payroll has no
    knowledge of loans.

    The deduction *amount* is computed fresh on every action_compute()
    (safe to recompute — matches the base engine's own
    unlink-and-rebuild-lines behavior while draft/computed). The actual
    balance reduction only happens in action_confirm(), a one-time
    transition the base model already enforces via its own state check
    — recomputing a draft/computed payslip must never silently drain a
    loan balance twice.
    """

    _inherit = "deployfleet.payroll.payslip"

    def _active_loans(self):
        self.ensure_one()
        return self.env["deployfleet.loan"].search([
            ("employee_id", "=", self.employee_id.id), ("state", "=", "active"),
        ])

    def action_compute(self):
        result = super().action_compute()
        loan_rule = self.env.ref("deployfleet_loans.payroll_rule_loan_deduction")
        for payslip in self:
            total = sum(loan._deduction_for_payslip() for loan in payslip._active_loans())
            if total:
                self.env["deployfleet.payroll.payslip.line"].create({
                    "payslip_id": payslip.id, "rule_id": loan_rule.id, "amount": total,
                })
        return result

    def action_confirm(self):
        result = super().action_confirm()
        for payslip in self:
            for loan in payslip._active_loans():
                deduction = loan._deduction_for_payslip()
                if deduction:
                    loan.action_apply_deduction(deduction)
        return result
