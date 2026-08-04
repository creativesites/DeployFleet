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

    Also disqualifies a driver with an approved deployfleet.leave.request
    covering the shipment's requested pickup date — found missing during
    the Dispatch & Trips domain audit (docs/architecture/20-experience-
    implementation-strategy.md §6c): nothing anywhere in dispatch scoring
    checked driver availability, so a driver on approved leave could still
    be suggested and confirmed. This module already reads deployfleet.trip
    for the rest-hour/consecutive-day checks, so extending it to also read
    deployfleet.leave.request (added as a manifest dependency) keeps every
    scheduling-safety check in one place rather than splitting availability
    logic into deployfleet_dispatch itself.

    MIN_REST_HOURS/MAX_CONSECUTIVE_DRIVING_DAYS are simple constants for
    now, not yet company-configurable — promote them to a
    deployfleet.calculation.parameter-style setting if a real customer's
    regional rules differ from these defaults.
    """

    _inherit = "deployfleet.shipment"

    def _score_candidate(self, vehicle, driver):
        score = super()._score_candidate(vehicle, driver)
        if score is None or self._is_disqualified(vehicle, driver):
            return None
        return score

    def _is_disqualified(self, vehicle, driver):
        document_model = self.env["deployfleet.compliance.document"]
        return (
            document_model.has_expired_documents("deployfleet.vehicle", vehicle.id)
            or document_model.has_expired_documents("hr.employee", driver.id)
            or self._driver_violates_rest_hour(driver)
            or self._driver_violates_consecutive_driving_days(driver)
            or self._driver_on_approved_leave(driver)
        )

    def _driver_on_approved_leave(self, driver):
        self.ensure_one()
        if not self.requested_pickup_date:
            return False
        pickup_date = self.requested_pickup_date.date()
        return bool(self.env["deployfleet.leave.request"].search_count([
            ("employee_id", "=", driver.id),
            ("state", "=", "approved"),
            ("date_from", "<=", pickup_date),
            ("date_to", ">=", pickup_date),
        ]))

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
