from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetMaintenancePrediction(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Prediction Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Prediction Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "PRED-001", "model_id": model.id, "status": "available",
        })

    def _create_fuel_log(self, days_ago, odometer, liters):
        return self.env["deployfleet.fuel.log"].create({
            "vehicle_id": self.vehicle.id,
            "date": fields.Date.today() - timedelta(days=days_ago),
            "odometer": odometer,
            "liters": liters,
        })

    def test_worsening_consumption_trend_raises_risk_score(self):
        self._create_fuel_log(60, 1000, 8.0)
        self._create_fuel_log(50, 1100, 8.0)
        self._create_fuel_log(40, 1200, 10.0)
        self._create_fuel_log(30, 1300, 13.0)

        prediction = self.env["deployfleet.maintenance.prediction"]._compute_for_vehicle(self.vehicle)
        self.assertGreater(prediction.consumption_trend_slope, 0.0)
        self.assertGreater(prediction.risk_score, 0.0)

    def test_recent_job_cards_counted_in_window(self):
        self.env["deployfleet.workshop.job.card"].create({
            "vehicle_id": self.vehicle.id,
            "opened_date": fields.Date.today() - timedelta(days=10),
        })
        self.env["deployfleet.workshop.job.card"].create({
            "vehicle_id": self.vehicle.id,
            "opened_date": fields.Date.today() - timedelta(days=200),  # outside the 90-day window
        })
        prediction = self.env["deployfleet.maintenance.prediction"]._compute_for_vehicle(self.vehicle)
        self.assertEqual(prediction.recent_job_card_count, 1)

    def test_no_history_gives_low_risk(self):
        prediction = self.env["deployfleet.maintenance.prediction"]._compute_for_vehicle(self.vehicle)
        self.assertEqual(prediction.risk_score, 0.0)
        self.assertEqual(prediction.risk_level, "low")

    def test_cron_computes_for_all_non_retired_vehicles(self):
        before = self.env["deployfleet.maintenance.prediction"].search_count([])
        self.env["deployfleet.maintenance.prediction"]._cron_compute_all()
        after = self.env["deployfleet.maintenance.prediction"].search_count([])
        self.assertGreater(after, before)
