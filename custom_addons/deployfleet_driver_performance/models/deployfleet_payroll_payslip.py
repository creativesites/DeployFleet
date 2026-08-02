from odoo import models


class DeployfleetPayrollPayslip(models.Model):
    """Adds the optional driver-performance payroll deduction from this
    module (not from deployfleet_payroll itself), same pattern as
    deployfleet_loans' extension of this same model."""

    _inherit = "deployfleet.payroll.payslip"

    def _driver_performance_events_for_period(self):
        self.ensure_one()
        return self.env["deployfleet.driver.performance.event"].search([
            ("driver_id", "=", self.employee_id.id),
            ("date", ">=", self.period_start), ("date", "<=", self.period_end),
            ("payroll_deduction_amount", ">", 0),
            ("payroll_deduction_applied", "=", False),
        ])

    def action_compute(self):
        result = super().action_compute()
        deduction_rule = self.env.ref("deployfleet_driver_performance.payroll_rule_driver_performance_deduction")
        for payslip in self:
            events = payslip._driver_performance_events_for_period()
            total = sum(events.mapped("payroll_deduction_amount"))
            if total:
                self.env["deployfleet.payroll.payslip.line"].create({
                    "payslip_id": payslip.id, "rule_id": deduction_rule.id, "amount": total,
                })
        return result

    def action_confirm(self):
        result = super().action_confirm()
        for payslip in self:
            payslip._driver_performance_events_for_period().write({"payroll_deduction_applied": True})
        return result
