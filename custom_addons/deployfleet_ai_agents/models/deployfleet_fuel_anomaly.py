from odoo import api, fields, models

from ..lib import stats

_ZSCORE_ANOMALY_THRESHOLD = 2.0


class DeployfleetFuelAnomaly(models.Model):
    """Statistical upgrade to deployfleet_fuel's flat 30%-above-average
    threshold rule (`deployfleet.fuel.log.is_anomaly`) - see that model's
    own docstring: "even a simple threshold rule is worth shipping before
    the predictive version lands in Phase 5." This is that version: a
    fill-up is flagged when its consumption is more than
    `_ZSCORE_ANOMALY_THRESHOLD` population standard deviations from that
    vehicle's own trailing consumption distribution, not a fixed
    percentage - a vehicle with naturally high variance no longer gets
    flagged for normal variation the way the flat threshold would.
    """

    _name = "deployfleet.fuel.anomaly"
    _description = "DeployFleet Fuel Anomaly (Statistical)"
    _order = "z_score desc"

    fuel_log_id = fields.Many2one("deployfleet.fuel.log", required=True, ondelete="cascade")
    vehicle_id = fields.Many2one(related="fuel_log_id.vehicle_id", store=True)
    z_score = fields.Float()
    detected_date = fields.Datetime(default=fields.Datetime.now, required=True)

    _sql_constraints = [
        ("fuel_log_unique", "UNIQUE(fuel_log_id)", "This fuel log has already been scored."),
    ]

    @api.model
    def _cron_detect_for_all_vehicles(self):
        vehicles = self.env["deployfleet.vehicle"].search([])  # pylint: disable=no-search-all
        for vehicle in vehicles:
            self._detect_for_vehicle(vehicle)

    @api.model
    def _detect_for_vehicle(self, vehicle):
        logs = self.env["deployfleet.fuel.log"].search([
            ("vehicle_id", "=", vehicle.id), ("consumption_l_per_100km", ">", 0),
        ], order="date asc")
        if len(logs) < 3:
            return self.browse()

        scores = stats.zscores(logs.mapped("consumption_l_per_100km"))
        already_scored_ids = set(self.search([("fuel_log_id", "in", logs.ids)]).fuel_log_id.ids)

        created = self.browse()
        for log, z_score in zip(logs, scores):
            if log.id in already_scored_ids or z_score < _ZSCORE_ANOMALY_THRESHOLD:
                continue
            created |= self.create({"fuel_log_id": log.id, "z_score": z_score})
        return created
