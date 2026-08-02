from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetDriverAdvance(TransactionCase):
    def setUp(self):
        super().setUp()
        self.driver = self.env["hr.employee"].create({"name": "Advance Driver", "deployfleet_is_driver": True})
        self.customer = self.env["res.partner"].create({"name": "Test Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id, "pickup_depot_id": self.pickup.id, "dropoff_depot_id": self.dropoff.id,
        })

    def test_advance_defaults_to_issued(self):
        advance = self.env["deployfleet.driver.advance"].create({
            "driver_id": self.driver.id, "amount": 200.0, "purpose": "fuel",
        })
        self.assertEqual(advance.state, "issued")

    def test_reconciled_amount_sums_expenses(self):
        advance = self.env["deployfleet.driver.advance"].create({
            "driver_id": self.driver.id, "amount": 200.0, "purpose": "fuel",
        })
        self.env["deployfleet.load.expense"].create({
            "shipment_id": self.shipment.id, "expense_type": "fuel", "amount": 120.0,
            "advance_id": advance.id,
        })
        self.env["deployfleet.load.expense"].create({
            "shipment_id": self.shipment.id, "expense_type": "toll", "amount": 30.0,
            "advance_id": advance.id,
        })
        self.assertEqual(advance.reconciled_amount, 150.0)
        self.assertEqual(advance.outstanding_amount, 50.0)

    def test_mark_reconciled_then_deducted_transitions(self):
        advance = self.env["deployfleet.driver.advance"].create({
            "driver_id": self.driver.id, "amount": 200.0, "purpose": "fuel",
        })
        advance.action_mark_reconciled()
        self.assertEqual(advance.state, "reconciled")
        advance.action_mark_deducted()
        self.assertEqual(advance.state, "deducted")

    def test_cannot_mark_deducted_before_reconciled(self):
        advance = self.env["deployfleet.driver.advance"].create({
            "driver_id": self.driver.id, "amount": 200.0, "purpose": "fuel",
        })
        with self.assertRaises(UserError):
            advance.action_mark_deducted()

    def test_cannot_reconcile_twice(self):
        advance = self.env["deployfleet.driver.advance"].create({
            "driver_id": self.driver.id, "amount": 200.0, "purpose": "fuel",
        })
        advance.action_mark_reconciled()
        with self.assertRaises(UserError):
            advance.action_mark_reconciled()
