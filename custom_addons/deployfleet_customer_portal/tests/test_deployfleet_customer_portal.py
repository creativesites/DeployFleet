from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetCustomerPortal(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer_a = self.env["res.partner"].create({"name": "Portal Customer A"})
        self.customer_b = self.env["res.partner"].create({"name": "Portal Customer B"})
        self.portal_user_a = self.env["res.users"].create({
            "name": "Portal User A",
            "login": "portal_a@example.com",
            "email": "portal_a@example.com",
            "partner_id": self.customer_a.id,
            "group_ids": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        pickup = self.env["deployfleet.depot"].create({"name": "Portal Pickup"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Portal Dropoff"})
        self.shipment_a = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer_a.id, "pickup_depot_id": pickup.id,
            "dropoff_depot_id": dropoff.id, "weight_kg": 100.0,
        })
        self.shipment_b = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer_b.id, "pickup_depot_id": pickup.id,
            "dropoff_depot_id": dropoff.id, "weight_kg": 100.0,
        })

    def test_portal_user_only_sees_own_shipments(self):
        visible = self.env["deployfleet.shipment"].with_user(self.portal_user_a).search([])
        self.assertIn(self.shipment_a, visible)
        self.assertNotIn(self.shipment_b, visible)

    def test_portal_user_cannot_read_other_customers_shipment(self):
        with self.assertRaises(AccessError):
            self.shipment_b.with_user(self.portal_user_a).check_access("read")

    def test_shipment_access_url_points_to_my_shipments(self):
        self.assertEqual(self.shipment_a.access_url, f"/my/shipments/{self.shipment_a.id}")
