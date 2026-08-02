from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetVehicle(TransactionCase):
    def _create_vehicle(self, **extra):
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        vals = {"license_plate": "TEST-001", "model_id": model.id}
        vals.update(extra)
        return self.env["deployfleet.vehicle"].create(vals)

    def test_creating_deployfleet_vehicle_creates_underlying_fleet_vehicle(self):
        vehicle = self._create_vehicle()
        self.assertTrue(vehicle.fleet_vehicle_id)
        self.assertEqual(vehicle.fleet_vehicle_id.license_plate, "TEST-001")

    def test_delegated_field_is_directly_accessible(self):
        vehicle = self._create_vehicle()
        # license_plate lives on fleet.vehicle but must be readable directly
        # on deployfleet.vehicle — that's the whole point of _inherits.
        self.assertEqual(vehicle.license_plate, "TEST-001")

    def test_default_status_is_available(self):
        vehicle = self._create_vehicle()
        self.assertEqual(vehicle.status, "available")

    def test_status_transition_actions(self):
        vehicle = self._create_vehicle()
        vehicle.action_set_breakdown()
        self.assertEqual(vehicle.status, "breakdown")
        vehicle.action_set_maintenance()
        self.assertEqual(vehicle.status, "maintenance")
        vehicle.action_set_available()
        self.assertEqual(vehicle.status, "available")

    def test_retiring_clears_current_driver(self):
        vehicle = self._create_vehicle()
        vehicle.action_set_retired()
        self.assertEqual(vehicle.status, "retired")
        self.assertFalse(vehicle.current_driver_id)

    def test_retired_vehicle_cannot_have_driver_assigned(self):
        driver = self.env["hr.employee"].create({"name": "Test Driver", "deployfleet_is_driver": True})
        vehicle = self._create_vehicle(status="retired")
        with self.assertRaises(ValidationError):
            vehicle.current_driver_id = driver

    def test_vehicle_type_assignment(self):
        vehicle_type = self.env.ref("deployfleet_core.vehicle_type_tanker")
        vehicle = self._create_vehicle(vehicle_type_id=vehicle_type.id)
        self.assertEqual(vehicle.vehicle_type_id, vehicle_type)
