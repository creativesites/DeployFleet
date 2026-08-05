from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetPart(TransactionCase):
    def setUp(self):
        super().setUp()
        self.part = self.env["deployfleet.part"].create({
            "name": "Brake Pad Set", "quantity_on_hand": 10.0, "reorder_level": 5.0,
        })

    def test_not_low_stock_above_reorder_level(self):
        self.assertFalse(self.part.is_low_stock)

    def test_low_stock_at_or_below_reorder_level(self):
        self.part.quantity_on_hand = 5.0
        self.assertTrue(self.part.is_low_stock)

    def test_receive_stock_increases_quantity(self):
        self.part.action_receive_stock(5.0)
        self.assertEqual(self.part.quantity_on_hand, 15.0)

    def test_consume_stock_decreases_quantity(self):
        self.part.action_consume_stock(4.0)
        self.assertEqual(self.part.quantity_on_hand, 6.0)

    def test_cannot_consume_more_than_available(self):
        with self.assertRaises(UserError):
            self.part.action_consume_stock(20.0)

    def test_cannot_receive_non_positive_quantity(self):
        with self.assertRaises(UserError):
            self.part.action_receive_stock(0.0)

    def test_consume_stock_reads_current_db_quantity_not_a_stale_cache(self):
        """Regression test for an engineering-audit finding (C-15): the
        old implementation decremented self.quantity_on_hand (the ORM's
        already-read, in-memory value) rather than re-reading the row -
        under a concurrent write this let a caller commit a decrement
        based on stock levels that were no longer current, silently
        losing part of a concurrent update. Updating the row directly
        via SQL (bypassing the recordset's ORM cache, simulating a
        concurrent writer) and then calling action_consume_stock() proves
        the fix reads the live row, not the stale cached value."""
        self.env.cr.execute(
            "UPDATE deployfleet_part SET quantity_on_hand = %s WHERE id = %s",
            (3.0, self.part.id),
        )
        # self.part's ORM cache still holds quantity_on_hand == 10.0 here.
        with self.assertRaises(UserError):
            self.part.action_consume_stock(5.0)
        self.part.invalidate_recordset(["quantity_on_hand"])
        self.assertEqual(self.part.quantity_on_hand, 3.0)
