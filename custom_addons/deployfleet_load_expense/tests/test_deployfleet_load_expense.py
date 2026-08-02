from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetLoadExpense(TransactionCase):
    def setUp(self):
        super().setUp()
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.env["deployfleet.vehicle"].create({
            "license_plate": "EXP-001", "model_id": model.id, "status": "available",
        })
        self.env["hr.employee"].create({"name": "Expense Driver", "deployfleet_is_driver": True})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": customer.id, "pickup_depot_id": pickup.id, "dropoff_depot_id": dropoff.id,
        })
        [assignment] = self.shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        self.trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])

    def test_create_expense_without_trip(self):
        expense = self.env["deployfleet.load.expense"].create({
            "shipment_id": self.shipment.id, "expense_type": "fuel", "amount": 500.0,
        })
        self.assertEqual(expense.expense_type, "fuel")

    def test_expense_with_trip_containing_shipment_is_valid(self):
        expense = self.env["deployfleet.load.expense"].create({
            "shipment_id": self.shipment.id, "trip_id": self.trip.id,
            "expense_type": "toll", "amount": 100.0,
        })
        self.assertEqual(expense.trip_id, self.trip)

    def test_expense_with_trip_not_containing_shipment_is_rejected(self):
        other_customer = self.env["res.partner"].create({"name": "Other Customer"})
        pickup = self.env["deployfleet.depot"].create({"name": "Other Pickup"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Other Dropoff"})
        unrelated_shipment = self.env["deployfleet.shipment"].create({
            "customer_id": other_customer.id, "pickup_depot_id": pickup.id, "dropoff_depot_id": dropoff.id,
        })
        with self.assertRaises(ValidationError):
            self.env["deployfleet.load.expense"].create({
                "shipment_id": unrelated_shipment.id, "trip_id": self.trip.id,
                "expense_type": "toll", "amount": 100.0,
            })

    def test_default_currency_is_company_currency(self):
        expense = self.env["deployfleet.load.expense"].create({
            "shipment_id": self.shipment.id, "expense_type": "fuel", "amount": 500.0,
        })
        self.assertEqual(expense.currency_id, self.env.company.currency_id)
