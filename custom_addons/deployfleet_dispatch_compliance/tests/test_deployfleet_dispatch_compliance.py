from datetime import datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DeployfleetDispatchComplianceTestBase(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "DC-001", "model_id": model.id, "status": "available",
        })
        self.driver = self.env["hr.employee"].create({"name": "Compliance Driver", "deployfleet_is_driver": True})
        self.customer = self.env["res.partner"].create({"name": "Test Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})

    def _create_shipment(self, **extra):
        vals = {
            "customer_id": self.customer.id, "pickup_depot_id": self.pickup.id, "dropoff_depot_id": self.dropoff.id,
        }
        vals.update(extra)
        return self.env["deployfleet.shipment"].create(vals)

    def _create_trip(self, planned_departure, planned_arrival, state="completed"):
        assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": self._create_shipment(requested_pickup_date=planned_departure).id,
            "vehicle_id": self.vehicle.id, "driver_id": self.driver.id,
        })
        return self.env["deployfleet.trip"].create({
            "dispatch_assignment_id": assignment.id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id,
            "planned_departure": planned_departure, "planned_arrival": planned_arrival,
            "actual_departure": planned_departure, "actual_arrival": planned_arrival, "state": state,
        })


class TestDeployfleetComplianceDocumentDisqualify(DeployfleetDispatchComplianceTestBase):
    def test_vehicle_with_expired_document_is_disqualified(self):
        doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "Insurance", "code": "insurance_test", "applies_to_model": "deployfleet.vehicle",
        })
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": doc_type.id, "res_model": "deployfleet.vehicle", "res_id": self.vehicle.id,
            "expiry_date": datetime.now().date() - timedelta(days=1),
        })
        shipment = self._create_shipment()
        self.assertIsNone(shipment._score_candidate(self.vehicle, self.driver))

    def test_driver_with_expired_document_is_disqualified(self):
        doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "License", "code": "license_test", "applies_to_model": "hr.employee",
        })
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": doc_type.id, "res_model": "hr.employee", "res_id": self.driver.id,
            "expiry_date": datetime.now().date() - timedelta(days=1),
        })
        shipment = self._create_shipment()
        self.assertIsNone(shipment._score_candidate(self.vehicle, self.driver))

    def test_no_documents_is_not_disqualified(self):
        shipment = self._create_shipment()
        self.assertIsNotNone(shipment._score_candidate(self.vehicle, self.driver))


class TestDeployfleetRestHourConstraint(DeployfleetDispatchComplianceTestBase):
    def test_insufficient_rest_disqualifies_driver(self):
        last_arrival = datetime.now() - timedelta(hours=2)
        self._create_trip(last_arrival - timedelta(hours=5), last_arrival)
        shipment = self._create_shipment(requested_pickup_date=last_arrival + timedelta(hours=1))
        self.assertIsNone(shipment._score_candidate(self.vehicle, self.driver))

    def test_sufficient_rest_does_not_disqualify_driver(self):
        last_arrival = datetime.now() - timedelta(hours=20)
        self._create_trip(last_arrival - timedelta(hours=5), last_arrival)
        shipment = self._create_shipment(requested_pickup_date=datetime.now())
        self.assertIsNotNone(shipment._score_candidate(self.vehicle, self.driver))


class TestDeployfleetConsecutiveDrivingDaysConstraint(DeployfleetDispatchComplianceTestBase):
    def test_six_consecutive_driving_days_disqualifies_driver(self):
        base = datetime.now() - timedelta(days=7)
        for day_offset in range(6):
            departure = base + timedelta(days=day_offset, hours=6)
            self._create_trip(departure, departure + timedelta(hours=2))
        shipment = self._create_shipment(requested_pickup_date=base + timedelta(days=6, hours=6))
        self.assertIsNone(shipment._score_candidate(self.vehicle, self.driver))

    def test_fewer_than_six_consecutive_driving_days_does_not_disqualify(self):
        base = datetime.now() - timedelta(days=4)
        for day_offset in range(2):
            departure = base + timedelta(days=day_offset, hours=6)
            self._create_trip(departure, departure + timedelta(hours=2))
        shipment = self._create_shipment(requested_pickup_date=base + timedelta(days=4, hours=6))
        self.assertIsNotNone(shipment._score_candidate(self.vehicle, self.driver))


class TestDeployfleetDriverAvailabilityConstraint(DeployfleetDispatchComplianceTestBase):
    def _approve_leave(self, date_from, date_to):
        leave_type = self.env["deployfleet.leave.type"].create({"name": "Test Leave Type"})
        request = self.env["deployfleet.leave.request"].create({
            "employee_id": self.driver.id, "leave_type_id": leave_type.id,
            "date_from": date_from, "date_to": date_to,
        })
        request.action_submit()
        request.action_approve()
        return request

    def test_driver_on_approved_leave_covering_pickup_date_is_disqualified(self):
        pickup = datetime.now() + timedelta(days=5)
        self._approve_leave(pickup.date() - timedelta(days=1), pickup.date() + timedelta(days=1))
        shipment = self._create_shipment(requested_pickup_date=pickup)
        self.assertIsNone(shipment._score_candidate(self.vehicle, self.driver))

    def test_driver_on_approved_leave_not_covering_pickup_date_is_not_disqualified(self):
        pickup = datetime.now() + timedelta(days=5)
        self._approve_leave(pickup.date() + timedelta(days=10), pickup.date() + timedelta(days=12))
        shipment = self._create_shipment(requested_pickup_date=pickup)
        self.assertIsNotNone(shipment._score_candidate(self.vehicle, self.driver))


class TestDeployfleetComplianceOverride(DeployfleetDispatchComplianceTestBase):
    def test_confirm_blocked_without_override_reason_when_document_expired(self):
        doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "Insurance", "code": "insurance_override_test", "applies_to_model": "deployfleet.vehicle",
        })
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": doc_type.id, "res_model": "deployfleet.vehicle", "res_id": self.vehicle.id,
            "expiry_date": datetime.now().date() - timedelta(days=1),
        })
        assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": self._create_shipment().id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id,
            "score": 100.0,
        })
        with self.assertRaises(UserError):
            assignment.action_confirm()

    def test_confirm_succeeds_with_override_reason_and_logs_it(self):
        doc_type = self.env["deployfleet.compliance.document.type"].create({
            "name": "Insurance", "code": "insurance_override_test2", "applies_to_model": "deployfleet.vehicle",
        })
        self.env["deployfleet.compliance.document"].create({
            "document_type_id": doc_type.id, "res_model": "deployfleet.vehicle", "res_id": self.vehicle.id,
            "expiry_date": datetime.now().date() - timedelta(days=1),
        })
        assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": self._create_shipment().id, "vehicle_id": self.vehicle.id, "driver_id": self.driver.id,
            "score": 100.0, "compliance_override_reason": "No compliant vehicle available; load cannot wait.",
        })
        assignment.action_confirm()
        self.assertEqual(assignment.state, "confirmed")
        log = self.env["deployfleet.dispatch.compliance.override.log"].search([
            ("assignment_id", "=", assignment.id),
        ])
        self.assertEqual(len(log), 1)
        self.assertTrue(log.vehicle_had_expired_documents)
