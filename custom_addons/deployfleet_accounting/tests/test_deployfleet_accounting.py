from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAccounting(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Accounting Customer"})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.env["deployfleet.depot"].create({"name": "Accounting Pickup"}).id,
            "dropoff_depot_id": self.env["deployfleet.depot"].create({"name": "Accounting Dropoff"}).id,
            "weight_kg": 500.0,
        })
        self.invoice = self.env["deployfleet.invoice"].create({
            "customer_id": self.customer.id,
            "line_ids": [
                (0, 0, {
                    "shipment_id": self.shipment.id,
                    "description": "Trip charge", "quantity": 1.0, "unit_amount": 2500.0,
                }),
            ],
        })

    def test_confirm_creates_and_posts_account_move(self):
        self.invoice.action_confirm()
        self.assertTrue(self.invoice.account_move_id)
        self.assertEqual(self.invoice.account_move_id.move_type, "out_invoice")
        self.assertEqual(self.invoice.account_move_id.partner_id, self.customer)
        self.assertEqual(self.invoice.account_move_id.state, "posted")
        self.assertEqual(self.invoice.account_move_id.amount_total, 2500.0)

    def test_confirm_registers_posted_event(self):
        before = self.env["deployfleet.event.log"].search_count([
            ("name", "=", "deployfleet.invoice.posted"),
        ])
        self.invoice.action_confirm()
        after = self.env["deployfleet.event.log"].search_count([
            ("name", "=", "deployfleet.invoice.posted"),
        ])
        self.assertEqual(after, before + 1)

    def test_confirm_is_idempotent_for_account_move_creation(self):
        self.invoice.action_confirm()
        move = self.invoice.account_move_id
        self.invoice.action_confirm()
        self.assertEqual(self.invoice.account_move_id, move)
