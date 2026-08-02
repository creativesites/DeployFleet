from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetContract(TransactionCase):
    def test_contract_gets_auto_reference(self):
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        contract = self.env["deployfleet.contract"].create({"customer_id": customer.id})
        self.assertTrue(contract.name.startswith("CNT"))

    def test_activate_and_terminate(self):
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        contract = self.env["deployfleet.contract"].create({"customer_id": customer.id})
        self.assertEqual(contract.state, "draft")
        contract.action_activate()
        self.assertEqual(contract.state, "active")
        contract.action_terminate()
        self.assertEqual(contract.state, "terminated")

    def test_cron_expires_stale_active_contract(self):
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        contract = self.env["deployfleet.contract"].create({
            "customer_id": customer.id,
            "state": "active",
            "end_date": fields.Date.today() - timedelta(days=1),
        })
        expired = self.env["deployfleet.contract"]._cron_expire_contracts()
        self.assertIn(contract, expired)
        self.assertEqual(contract.state, "expired")

    def test_contract_without_end_date_is_a_spot_style_open_contract(self):
        """A contract with no end_date should never be auto-expired by the cron."""
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        contract = self.env["deployfleet.contract"].create({
            "customer_id": customer.id, "state": "active",
        })
        expired = self.env["deployfleet.contract"]._cron_expire_contracts()
        self.assertNotIn(contract, expired)
        self.assertEqual(contract.state, "active")


@tagged("post_install", "-at_install")
class TestDeployfleetDepot(TransactionCase):
    def test_depot_name_unique_per_company(self):
        self.env["deployfleet.depot"].create({"name": "Lusaka Depot"})
        with self.assertRaises(Exception):
            self.env["deployfleet.depot"].create({"name": "Lusaka Depot"})
