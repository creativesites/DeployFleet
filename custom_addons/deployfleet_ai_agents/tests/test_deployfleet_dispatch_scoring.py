from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetDispatchScoring(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Scoring Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Scoring Pickup"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Scoring Dropoff"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Scoring Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Scoring Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "SCORE-001", "model_id": model.id, "status": "available",
        })
        self.driver = self.env["hr.employee"].create({"name": "Scoring Driver", "deployfleet_is_driver": True})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id, "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id, "weight_kg": 100.0,
        })

    def _create_historical_trip(self, on_time):
        shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id, "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id, "weight_kg": 100.0,
        })
        assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": shipment.id, "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id, "state": "confirmed",
        })
        now = fields.Datetime.now()
        return self.env["deployfleet.trip"].create({
            "dispatch_assignment_id": assignment.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id,
            "state": "completed", "planned_arrival": now,
            "actual_arrival": now if on_time else now + timedelta(hours=1),
        })

    def test_no_history_leaves_score_unchanged(self):
        baseline = self.shipment._score_candidate(self.vehicle, self.driver)
        self._create_historical_trip(on_time=True)
        # A driver with zero history gets a neutral 0.5 on-time prior, same
        # as what a single perfectly-on-time trip's rate (1.0) shifts away
        # from - so scoring a *fresh* driver/vehicle pair with no rows at
        # all must equal the un-adjusted base score.
        fresh_driver = self.env["hr.employee"].create({"name": "Fresh Driver", "deployfleet_is_driver": True})
        fresh_score = self.shipment._score_candidate(self.vehicle, fresh_driver)
        self.assertEqual(baseline, fresh_score)

    def test_on_time_history_raises_score(self):
        baseline = self.shipment._score_candidate(self.vehicle, self.driver)
        self._create_historical_trip(on_time=True)
        boosted = self.shipment._score_candidate(self.vehicle, self.driver)
        self.assertAlmostEqual(boosted - baseline, 10.0)  # (1.0 - 0.5) * _ON_TIME_RATE_WEIGHT(20)

    def test_late_history_lowers_score(self):
        baseline = self.shipment._score_candidate(self.vehicle, self.driver)
        self._create_historical_trip(on_time=False)
        lowered = self.shipment._score_candidate(self.vehicle, self.driver)
        self.assertAlmostEqual(lowered - baseline, -10.0)  # (0.0 - 0.5) * _ON_TIME_RATE_WEIGHT(20)

    def test_breakdown_history_lowers_score(self):
        baseline = self.shipment._score_candidate(self.vehicle, self.driver)
        self.env["deployfleet.event.log"].register_event(
            "deployfleet.vehicle.breakdown", "deployfleet.vehicle", self.vehicle.id, {}
        )
        after = self.shipment._score_candidate(self.vehicle, self.driver)
        self.assertAlmostEqual(after - baseline, -3.0)  # 1 event * _BREAKDOWN_PENALTY_PER_EVENT(3)

    def test_disqualified_candidate_still_returns_none(self):
        self.vehicle.status = "breakdown"
        self.assertIsNone(self.shipment._score_candidate(self.vehicle, self.driver))
