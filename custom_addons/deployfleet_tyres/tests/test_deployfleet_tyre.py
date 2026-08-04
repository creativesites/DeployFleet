from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetTyre(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "TYRE-001", "model_id": model.id,
        })

    def test_create_tyre_defaults_to_fitted(self):
        tyre = self.env["deployfleet.tyre"].create({
            "vehicle_id": self.vehicle.id, "position": "front_left",
        })
        self.assertEqual(tyre.state, "fitted")

    def test_two_active_tyres_at_same_position_rejected(self):
        self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        with self.assertRaises(ValidationError):
            self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})

    def test_scrapping_then_refitting_same_position_is_allowed(self):
        first = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        first.action_scrap()
        second = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        self.assertEqual(second.state, "fitted")

    def test_record_reading_updates_tread_depth_and_logs_history(self):
        tyre = self.env["deployfleet.tyre"].create({
            "vehicle_id": self.vehicle.id, "position": "front_left", "tread_depth_mm": 10.0,
        })
        tyre.action_record_reading(7.5, odometer=50000.0)
        self.assertEqual(tyre.tread_depth_mm, 7.5)
        self.assertEqual(len(tyre.reading_ids), 1)

    def test_rotate_updates_position_and_logs_event(self):
        tyre = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        tyre.action_rotate("rear_left_outer")
        self.assertEqual(tyre.position, "rear_left_outer")
        event = tyre.event_ids
        self.assertEqual(event.event_type, "rotation")
        self.assertEqual(event.from_position, "front_left")
        self.assertEqual(event.to_position, "rear_left_outer")

    def test_cannot_rotate_scrapped_tyre(self):
        tyre = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        tyre.action_scrap()
        with self.assertRaises(UserError):
            tyre.action_rotate("rear_left_outer")

    def test_cannot_scrap_twice(self):
        tyre = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        tyre.action_scrap()
        with self.assertRaises(UserError):
            tyre.action_scrap()

    def test_dispatcher_can_rotate_tyre(self):
        # Regression test for a real ACL gap found while building the
        # deployfleet_ui Tyre Manager screen: action_rotate/action_retread/
        # action_scrap all internally create a deployfleet.tyre.event
        # record, but the dispatcher group previously had create=0 on that
        # model even though it already had write=1 on the parent tyre
        # model - meaning these actions raised an AccessError for the
        # dispatcher role despite dispatcher clearly being meant to
        # perform them (the same operational authority dispatcher already
        # has for vehicle status transitions). Fixed in
        # security/ir.model.access.csv by granting dispatcher create=1 on
        # deployfleet.tyre.event.
        tyre = self.env["deployfleet.tyre"].create({"vehicle_id": self.vehicle.id, "position": "front_left"})
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Test Dispatcher", "login": "test_dispatcher@example.com",
            "email": "test_dispatcher@example.com", "group_ids": [(6, 0, [dispatcher_group.id])],
        })
        tyre.with_user(dispatcher_user).action_rotate("rear_left_outer")
        self.assertEqual(tyre.position, "rear_left_outer")
