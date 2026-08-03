from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetFuelAnomaly(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Anomaly Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Anomaly Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "ANOM-001", "model_id": model.id, "status": "available",
        })
        odometer = 1000
        for days_ago, liters in [(50, 0), (40, 8.0), (30, 8.0), (20, 8.0), (10, 30.0)]:
            self.env["deployfleet.fuel.log"].create({
                "vehicle_id": self.vehicle.id,
                "date": fields.Date.today() - timedelta(days=days_ago),
                "odometer": odometer,
                "liters": liters,
            })
            odometer += 100

    def test_detects_the_outlier_fill_up(self):
        anomalies = self.env["deployfleet.fuel.anomaly"]._detect_for_vehicle(self.vehicle)
        self.assertEqual(len(anomalies), 1)
        self.assertEqual(anomalies.fuel_log_id.liters, 30.0)
        self.assertGreaterEqual(anomalies.z_score, 2.0)

    def test_running_twice_does_not_duplicate(self):
        self.env["deployfleet.fuel.anomaly"]._detect_for_vehicle(self.vehicle)
        first_count = self.env["deployfleet.fuel.anomaly"].search_count([])
        self.env["deployfleet.fuel.anomaly"]._detect_for_vehicle(self.vehicle)
        second_count = self.env["deployfleet.fuel.anomaly"].search_count([])
        self.assertEqual(first_count, second_count)

    def test_too_few_logs_detects_nothing(self):
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        other_vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "ANOM-002", "model_id": model.id, "status": "available",
        })
        anomalies = self.env["deployfleet.fuel.anomaly"]._detect_for_vehicle(other_vehicle)
        self.assertFalse(anomalies)
