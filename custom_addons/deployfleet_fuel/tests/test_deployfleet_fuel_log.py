from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetFuelLog(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "FUEL-001", "model_id": model.id,
        })

    def test_first_log_has_no_consumption(self):
        log = self.env["deployfleet.fuel.log"].create({
            "vehicle_id": self.vehicle.id, "odometer": 10000.0, "liters": 100.0,
        })
        self.assertEqual(log.distance_since_last_km, 0.0)
        self.assertEqual(log.consumption_l_per_100km, 0.0)
        self.assertFalse(log.is_anomaly)

    def test_consumption_computed_from_previous_log(self):
        self.env["deployfleet.fuel.log"].create({
            "vehicle_id": self.vehicle.id, "date": "2026-01-01", "odometer": 10000.0, "liters": 100.0,
        })
        second = self.env["deployfleet.fuel.log"].create({
            "vehicle_id": self.vehicle.id, "date": "2026-01-05", "odometer": 10500.0, "liters": 150.0,
        })
        self.assertEqual(second.distance_since_last_km, 500.0)
        self.assertEqual(second.consumption_l_per_100km, 30.0)

    def test_anomaly_flagged_when_far_above_trailing_average(self):
        for i in range(3):
            self.env["deployfleet.fuel.log"].create({
                "vehicle_id": self.vehicle.id, "date": f"2026-01-0{i + 1}",
                "odometer": 10000.0 + i * 500.0, "liters": 150.0,
            })
        anomaly = self.env["deployfleet.fuel.log"].create({
            "vehicle_id": self.vehicle.id, "date": "2026-01-10", "odometer": 11700.0, "liters": 400.0,
        })
        self.assertTrue(anomaly.is_anomaly)
