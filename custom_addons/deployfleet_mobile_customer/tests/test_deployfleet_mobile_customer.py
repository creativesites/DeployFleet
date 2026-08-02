import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetMobileCustomerController(HttpCase):
    def setUp(self):
        super().setUp()
        self.customer_a = self.env["res.partner"].create({"name": "Mobile Customer A"})
        self.customer_b = self.env["res.partner"].create({"name": "Mobile Customer B"})
        self.portal_user_a = self.env["res.users"].create({
            "name": "Mobile Portal User A",
            "login": "mobile_customer_a@example.com",
            "email": "mobile_customer_a@example.com",
            "password": "Test1234!",
            "partner_id": self.customer_a.id,
            "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
        })
        pickup = self.env["deployfleet.depot"].create({"name": "Mobile Pickup"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Mobile Dropoff"})
        self.shipment_a = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer_a.id, "pickup_depot_id": pickup.id,
            "dropoff_depot_id": dropoff.id, "weight_kg": 200.0,
        })
        self.shipment_b = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer_b.id, "pickup_depot_id": pickup.id,
            "dropoff_depot_id": dropoff.id, "weight_kg": 200.0,
        })

    def test_shipments_denied_without_login(self):
        self.authenticate(None, None)
        response = self.url_open("/api/mobile/customer/shipments")
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_shipments_returns_only_own_shipments(self):
        self.authenticate("mobile_customer_a@example.com", "Test1234!")
        response = self.url_open("/api/mobile/customer/shipments")
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        ids = [item["id"] for item in data["data"]]
        self.assertIn(self.shipment_a.id, ids)
        self.assertNotIn(self.shipment_b.id, ids)

    def test_shipment_detail_for_other_customer_is_not_found(self):
        self.authenticate("mobile_customer_a@example.com", "Test1234!")
        response = self.url_open(f"/api/mobile/customer/shipments/{self.shipment_b.id}")
        self.assertEqual(response.status_code, 404)
