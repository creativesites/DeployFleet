from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetDriver(TransactionCase):
    def test_default_driver_not_expired_without_license(self):
        employee = self.env["hr.employee"].create({"name": "Test Driver", "deployfleet_is_driver": True})
        self.assertFalse(employee.deployfleet_license_is_expired)

    def test_future_expiry_is_not_expired(self):
        employee = self.env["hr.employee"].create({
            "name": "Test Driver",
            "deployfleet_is_driver": True,
            "deployfleet_license_expiry": fields.Date.today() + timedelta(days=10),
        })
        self.assertFalse(employee.deployfleet_license_is_expired)

    def test_past_expiry_is_expired(self):
        employee = self.env["hr.employee"].create({
            "name": "Test Driver",
            "deployfleet_is_driver": True,
            "deployfleet_license_expiry": fields.Date.today() - timedelta(days=1),
        })
        self.assertTrue(employee.deployfleet_license_is_expired)

    def test_qualified_vehicle_types_assignment(self):
        rigid = self.env.ref("deployfleet_core.vehicle_type_rigid")
        articulated = self.env.ref("deployfleet_core.vehicle_type_articulated")
        employee = self.env["hr.employee"].create({
            "name": "Test Driver",
            "deployfleet_is_driver": True,
            "deployfleet_qualified_vehicle_type_ids": [(6, 0, [rigid.id, articulated.id])],
        })
        self.assertEqual(len(employee.deployfleet_qualified_vehicle_type_ids), 2)

    def test_default_risk_score(self):
        employee = self.env["hr.employee"].create({"name": "Test Driver", "deployfleet_is_driver": True})
        self.assertEqual(employee.deployfleet_risk_score, 100.0)

    def test_driver_action_exists_and_targets_hr_employee(self):
        action = self.env.ref("deployfleet_driver.action_deployfleet_driver")
        self.assertEqual(action.res_model, "hr.employee")

    def test_is_driver_flag_filters_search(self):
        self.env["hr.employee"].create({"name": "Non-Driver Staff", "deployfleet_is_driver": False})
        driver = self.env["hr.employee"].create({"name": "Driver Staff", "deployfleet_is_driver": True})
        found = self.env["hr.employee"].search([("deployfleet_is_driver", "=", True)])
        self.assertIn(driver, found)
        self.assertTrue(all(rec.deployfleet_is_driver for rec in found))
