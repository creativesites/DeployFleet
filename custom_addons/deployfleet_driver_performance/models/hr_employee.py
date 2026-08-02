from datetime import timedelta

from odoo import fields, models

BASE_RELIABILITY_SCORE = 100.0
TRAILING_WINDOW_DAYS = 365


class HrEmployee(models.Model):
    """Adds the reliability score from this module (not from
    deployfleet_driver), the same classical-extension pattern
    deployfleet_driver itself already uses on hr.employee — see
    docs/architecture/CLAUDE.md's naming table."""

    _inherit = "hr.employee"

    deployfleet_reliability_score = fields.Float(compute="_compute_deployfleet_reliability_score")

    def _compute_deployfleet_reliability_score(self):
        # Not stored: derived from deployfleet.driver.performance.event
        # records with no direct FK back to hr.employee's own field
        # dependency graph, same reasoning as deployfleet_leave's
        # used_days/remaining_days — computing fresh on every read is
        # simpler and correct.
        event_model = self.env["deployfleet.driver.performance.event"]
        cutoff = fields.Date.context_today(self) - timedelta(days=TRAILING_WINDOW_DAYS)
        for employee in self:
            events = event_model.search([("driver_id", "=", employee.id), ("date", ">=", cutoff)])
            score = BASE_RELIABILITY_SCORE + sum(events.mapped("score_impact"))
            employee.deployfleet_reliability_score = max(0.0, min(BASE_RELIABILITY_SCORE, score))
