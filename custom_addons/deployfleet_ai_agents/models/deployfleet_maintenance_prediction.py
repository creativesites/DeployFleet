from datetime import timedelta

from odoo import api, fields, models

from ..lib import stats

_WINDOW_DAYS = 90
_TREND_WEIGHT = 60.0
_JOB_CARD_WEIGHT = 40.0
_JOB_CARD_SATURATION = 4
_TREND_SATURATION_SLOPE = 6.0


class DeployfleetMaintenancePrediction(models.Model):
    """Predictive maintenance: failure-risk scoring per vehicle, distinct
    from deployfleet_maintenance's rule-based odometer/calendar scheduling
    (Phase 2) - see docs/architecture/08-ai-architecture.md §11's explicit
    distinction between the two. Combines two real signals into a single
    0-100 risk score: a rising fuel-consumption trend (least-squares slope
    over deployfleet.fuel.log's consumption_l_per_100km) and recent
    workshop repair frequency (deployfleet.workshop.job.card count in a
    trailing window)."""

    _name = "deployfleet.maintenance.prediction"
    _description = "DeployFleet Predictive Maintenance Score"
    _order = "risk_score desc"

    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True, ondelete="cascade")
    computed_date = fields.Datetime(default=fields.Datetime.now, required=True)
    consumption_trend_slope = fields.Float(
        help="L/100km change per fill-up; positive means worsening fuel efficiency."
    )
    recent_job_card_count = fields.Integer(help="Workshop job cards opened in the trailing window.")
    risk_score = fields.Float(help="0-100, higher means higher predicted failure risk.")
    risk_level = fields.Selection(
        [("low", "Low"), ("medium", "Medium"), ("high", "High")], required=True, default="low"
    )
    basis = fields.Text(help="Plain-language explanation of what drove this score.")

    @api.model
    def _compute_for_vehicle(self, vehicle):
        window_start = fields.Date.context_today(self) - timedelta(days=_WINDOW_DAYS)
        logs = self.env["deployfleet.fuel.log"].search([
            ("vehicle_id", "=", vehicle.id),
            ("date", ">=", window_start),
            ("consumption_l_per_100km", ">", 0),
        ], order="date asc")

        slope = 0.0
        if len(logs) >= 3:
            xs = list(range(len(logs)))
            ys = logs.mapped("consumption_l_per_100km")
            slope, _intercept = stats.linear_regression(xs, ys)

        job_cards = self.env["deployfleet.workshop.job.card"].search_count([
            ("vehicle_id", "=", vehicle.id), ("opened_date", ">=", window_start),
        ])

        trend_component = min(max(slope, 0.0) / _TREND_SATURATION_SLOPE, 1.0) * _TREND_WEIGHT
        job_card_component = min(job_cards / _JOB_CARD_SATURATION, 1.0) * _JOB_CARD_WEIGHT
        risk_score = round(trend_component + job_card_component, 1)
        risk_level = "high" if risk_score >= 60 else "medium" if risk_score >= 30 else "low"

        if slope > 0:
            trend_line = (
                f"Fuel consumption trending up ~{slope:.2f} L/100km per fill-up "
                f"over the last {_WINDOW_DAYS} days."
            )
        else:
            trend_line = f"No worsening fuel-consumption trend detected over the last {_WINDOW_DAYS} days."

        return self.create({
            "vehicle_id": vehicle.id,
            "consumption_trend_slope": slope,
            "recent_job_card_count": job_cards,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "basis": f"{trend_line}\n{job_cards} workshop job card(s) opened in the last {_WINDOW_DAYS} days.",
        })

    @api.model
    def _cron_compute_all(self):
        vehicles = self.env["deployfleet.vehicle"].search([("status", "!=", "retired")])
        for vehicle in vehicles:
            self._compute_for_vehicle(vehicle)
