from datetime import date, datetime, time, timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetLeaveRequest(TransactionCase):
    def setUp(self):
        super().setUp()
        self.driver = self.env["hr.employee"].create({"name": "Leave Driver", "deployfleet_is_driver": True})
        self.leave_type = self.env.ref("deployfleet_leave.leave_type_annual")

    def _create_request(self, **extra):
        vals = {
            "employee_id": self.driver.id, "leave_type_id": self.leave_type.id,
            "date_from": date.today() + timedelta(days=10), "date_to": date.today() + timedelta(days=14),
        }
        vals.update(extra)
        return self.env["deployfleet.leave.request"].create(vals)

    def test_number_of_days_computed_inclusive(self):
        request = self._create_request(
            date_from=date.today(), date_to=date.today() + timedelta(days=4),
        )
        self.assertEqual(request.number_of_days, 5)

    def test_end_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            self._create_request(date_from=date.today() + timedelta(days=5), date_to=date.today())

    def test_full_workflow(self):
        request = self._create_request()
        request.action_submit()
        self.assertEqual(request.state, "submitted")
        request.action_approve()
        self.assertEqual(request.state, "approved")

    def test_cannot_submit_twice(self):
        request = self._create_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_submit()

    def test_approval_blocked_by_conflicting_trip(self):
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "LEAVE-001", "model_id": model.id, "status": "available",
        })
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})
        conflicting_departure = datetime.combine(date.today() + timedelta(days=12), time(8, 0))
        shipment = self.env["deployfleet.shipment"].create({
            "customer_id": customer.id, "pickup_depot_id": pickup.id, "dropoff_depot_id": dropoff.id,
            "requested_pickup_date": conflicting_departure,
        })
        assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": shipment.id, "vehicle_id": vehicle.id, "driver_id": self.driver.id,
            "planned_departure": conflicting_departure, "score": 100.0,
        })
        assignment.action_confirm()

        request = self._create_request()
        request.action_submit()
        with self.assertRaises(UserError):
            request.action_approve()

    def test_cancel_from_approved(self):
        request = self._create_request()
        request.action_submit()
        request.action_approve()
        request.action_cancel()
        self.assertEqual(request.state, "cancelled")

    def test_driver_can_submit_own_leave_request(self):
        # Regression test for a real ACL gap found while building the
        # deployfleet_ui Driver & HR domain: the driver group previously
        # had create=1 but write=0 on this model, so a driver could file
        # a leave request but could never call action_submit() on it
        # themselves (it writes internally). Fixed by granting write=1
        # in ir.model.access.csv plus a new ir.rule
        # (deployfleet_leave_request_rule_driver_own) scoping driver
        # access to their own employee's requests only.
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        driver_user = self.env["res.users"].create({
            "name": "Test Driver User", "login": "test_driver_user@example.com",
            "email": "test_driver_user@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        self.driver.user_id = driver_user.id
        request = self._create_request()
        request.with_user(driver_user).action_submit()
        self.assertEqual(request.state, "submitted")

    def test_driver_cannot_write_another_drivers_leave_request(self):
        # The write grant above must not become a company-wide
        # free-for-all: the new ir.rule should still block a driver from
        # submitting a *different* driver's leave request.
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        other_driver_user = self.env["res.users"].create({
            "name": "Other Driver User", "login": "other_driver_user@example.com",
            "email": "other_driver_user@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        self.env["hr.employee"].create({
            "name": "Other Driver", "deployfleet_is_driver": True, "user_id": other_driver_user.id,
        })
        request = self._create_request()  # belongs to self.driver, not other_driver_user
        with self.assertRaises(AccessError):
            request.with_user(other_driver_user).action_submit()

    def test_dispatcher_can_approve_another_employees_leave_request(self):
        # Regression test for the engineering-audit finding: because
        # group_deployfleet_manager implies group_deployfleet_dispatcher
        # implies group_deployfleet_driver, the driver-own ir.rule above
        # was the model's ONLY rule and silently restricted every
        # dispatcher/manager/owner to their own (nonexistent) employee
        # record too — nobody but the requester could ever see or
        # approve a leave request. Fixed with a second, broader rule
        # (deployfleet_leave_request_rule_dispatcher_all) for the
        # dispatcher group and everything that implies it.
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Test Dispatcher User", "login": "test_dispatcher_user@example.com",
            "email": "test_dispatcher_user@example.com", "group_ids": [(6, 0, [dispatcher_group.id])],
        })
        request = self._create_request()  # belongs to self.driver, not dispatcher_user
        request.action_submit()
        request.with_user(dispatcher_user).action_approve()
        self.assertEqual(request.state, "approved")

    def test_driver_cannot_self_approve_leave_request(self):
        # Defense-in-depth regression test: a driver who legitimately
        # has write access to their own leave request (per the ir.rule
        # above) must still not be able to call action_approve()/
        # action_reject() on it themselves — that would defeat the
        # point of an approval workflow. The view hides these buttons
        # for the driver role, but per this project's own stated
        # principle a view restriction is a UI convenience, not a
        # security boundary, so the check must also live in Python.
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        driver_user = self.env["res.users"].create({
            "name": "Self Approve Driver User", "login": "self_approve_driver_user@example.com",
            "email": "self_approve_driver_user@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        self.driver.user_id = driver_user.id
        request = self._create_request()
        request.with_user(driver_user).action_submit()
        with self.assertRaises(UserError):
            request.with_user(driver_user).action_approve()
