from datetime import date, datetime, time, timedelta

from odoo.exceptions import UserError, ValidationError
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
