from datetime import timedelta

from odoo import models

MIN_REST_HOURS = 8
MAX_CONSECUTIVE_DRIVING_DAYS = 6


class DeployfleetShipment(models.Model):
    """Extends `_score_candidate()` (from deployfleet_dispatch) with the
    hard constraints docs/architecture/06-risks-and-recommendations.md
    risk #3 calls for: expired driver/vehicle compliance documents, and
    driver rest-hour / consecutive-driving-day limits — the safety/
    regulatory stakes make these core scope here, not a deferred
    nice-to-have.

    MIN_REST_HOURS/MAX_CONSECUTIVE_DRIVING_DAYS are simple constants for
    now, not yet company-configurable — promote them to a
    deployfleet.calculation.parameter-style setting if a real customer's
    regional rules differ from these defaults.
    """

    _inherit = "deployfleet.shipment"

    def _score_candidate(self, vehicle, driver):
        score = super()._score_candidate(vehicle, driver)
        if score is None:
            return None

        document_model = self.env["deployfleet.compliance.document"]
        if document_model.has_expired_documents("deployfleet.vehicle", vehicle.id):
            return None
        if document_model.has_expired_documents("hr.employee", driver.id):
            return None

        if self._driver_violates_rest_hour(driver):
            return None
        if self._driver_violates_consecutive_driving_days(driver):
            return None

        return score

    def _driver_recent_trips(self, driver):
        return self.env["deployfleet.trip"].search([
            ("driver_id", "=", driver.id),
            ("state", "in", ("departed", "completed")),
        ], order="planned_departure desc", limit=10)

    def _driver_violates_rest_hour(self, driver):
        self.ensure_one()
        if not self.requested_pickup_date:
            return False
        last_trip = self._driver_recent_trips(driver)[:1]
        if not last_trip:
            return False
        last_arrival = last_trip.actual_arrival or last_trip.planned_arrival
        if not last_arrival:
            return False
        rest = self.requested_pickup_date - last_arrival
        return rest < timedelta(hours=MIN_REST_HOURS)

    def _driver_violates_consecutive_driving_days(self, driver):
        self.ensure_one()
        if not self.requested_pickup_date:
            return False
        driving_days = set()
        for trip in self._driver_recent_trips(driver):
            departure = trip.actual_departure or trip.planned_departure
            if departure:
                driving_days.add(departure.date())

        consecutive = 0
        day = self.requested_pickup_date.date() - timedelta(days=1)
        while day in driving_days:
            consecutive += 1
            day -= timedelta(days=1)
        return consecutive >= MAX_CONSECUTIVE_DRIVING_DAYS
