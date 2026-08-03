from datetime import timedelta

from odoo import fields, models

_BREAKDOWN_WINDOW_DAYS = 180
_ON_TIME_RATE_WEIGHT = 20.0
_BREAKDOWN_PENALTY_PER_EVENT = 3.0
_BREAKDOWN_PENALTY_CAP = 5


class DeployfleetShipment(models.Model):
    """Extends deployfleet_dispatch's weighted-heuristic scoring (Phase 1)
    with two historical-performance signals, per
    docs/architecture/05-implementation-roadmap.md Phase 5's "dispatch/
    route optimization": a driver's own on-time completion rate and a
    vehicle's own recent breakdown frequency (sourced from the
    `deployfleet.vehicle.breakdown` event already on the event bus).
    Disqualification (returning None) is left entirely to the base
    scoring - this only adjusts the score of candidates that already
    passed those hard checks."""

    _inherit = "deployfleet.shipment"

    def _score_candidate(self, vehicle, driver):
        score = super()._score_candidate(vehicle, driver)
        if score is None:
            return None
        on_time_rate = self._historical_driver_on_time_rate(driver)
        breakdown_count = self._historical_vehicle_breakdown_count(vehicle)
        score += (on_time_rate - 0.5) * _ON_TIME_RATE_WEIGHT
        score -= min(breakdown_count, _BREAKDOWN_PENALTY_CAP) * _BREAKDOWN_PENALTY_PER_EVENT
        return score

    def _historical_driver_on_time_rate(self, driver):
        trips = self.env["deployfleet.trip"].search([
            ("driver_id", "=", driver.id), ("state", "=", "completed"),
        ])
        if not trips:
            return 0.5  # no history yet - neutral prior, neither reward nor penalize
        on_time = trips.filtered(
            lambda trip: not trip.planned_arrival or not trip.actual_arrival
            or trip.actual_arrival <= trip.planned_arrival
        )
        return len(on_time) / len(trips)

    def _historical_vehicle_breakdown_count(self, vehicle):
        window_start = fields.Datetime.now() - timedelta(days=_BREAKDOWN_WINDOW_DAYS)
        return self.env["deployfleet.event.log"].search_count([
            ("name", "=", "deployfleet.vehicle.breakdown"),
            ("source_model", "=", "deployfleet.vehicle"),
            ("source_id", "=", vehicle.id),
            ("create_date", ">=", window_start),
        ])
