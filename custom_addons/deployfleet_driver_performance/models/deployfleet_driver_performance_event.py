from odoo import api, fields, models

DEFAULT_SCORE_IMPACT = {
    "accident": -20.0,
    "violation": -10.0,
    "harsh_braking": -2.0,
    "speeding": -5.0,
    "fuel_abuse": -5.0,
    "late_delivery": -3.0,
    "other": 0.0,
}


class DeployfleetDriverPerformanceEvent(models.Model):
    """A driver safety/performance signal — reframed from "discipline" per
    docs/architecture/04-module-structure.md: this is a safety/
    performance signal, not an HR conduct write-up. Feeds
    hr.employee.deployfleet_reliability_score (added in this module, see
    hr_employee.py) and, optionally, a payslip deduction (see
    deployfleet_payroll_payslip.py).
    """

    _name = "deployfleet.driver.performance.event"
    _description = "DeployFleet Driver Performance Event"
    _order = "date desc"
    _inherit = ["mail.thread"]

    driver_id = fields.Many2one(
        "hr.employee", required=True, domain=[("deployfleet_is_driver", "=", True)], tracking=True,
    )
    event_type = fields.Selection(
        [
            ("accident", "Accident"),
            ("violation", "Traffic Violation"),
            ("harsh_braking", "Harsh Braking"),
            ("speeding", "Speeding"),
            ("fuel_abuse", "Fuel Abuse Pattern"),
            ("late_delivery", "Late Delivery"),
            ("other", "Other"),
        ],
        required=True,
    )
    date = fields.Date(default=fields.Date.context_today, required=True)
    description = fields.Text()
    score_impact = fields.Float(help="Negative value subtracted from the driver's reliability score.")
    payroll_deduction_amount = fields.Monetary(
        help="Optional financial penalty. Leave at 0 for a safety signal with no payroll impact.",
    )
    payroll_deduction_applied = fields.Boolean(default=False, copy=False)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    @api.onchange("event_type")
    def _onchange_event_type_suggest_score_impact(self):
        # A suggestion the user can override, not an enforced value —
        # e.g. a minor fender-bender and a serious accident are both
        # "accident" but shouldn't always cost the same points.
        if self.event_type:
            self.score_impact = DEFAULT_SCORE_IMPACT.get(self.event_type, 0.0)
