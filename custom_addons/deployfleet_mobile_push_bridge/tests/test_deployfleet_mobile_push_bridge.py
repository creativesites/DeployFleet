import json
from unittest.mock import MagicMock, patch

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeployfleetMobileDeviceController(HttpCase):
    def setUp(self):
        super().setUp()
        self.user = self.env["res.users"].create({
            "name": "Push User", "login": "push_user@example.com",
            "email": "push_user@example.com", "password": "Test1234!",
        })

    def test_register_denied_without_login(self):
        self.authenticate(None, None)
        response = self.url_open("/api/mobile/push/register", data={"push_token": "tok", "platform": "ios"})
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_register_creates_device(self):
        self.authenticate("push_user@example.com", "Test1234!")
        response = self.url_open(
            "/api/mobile/push/register", data={"push_token": "ExponentPushToken[abc]", "platform": "android"}
        )
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        device = self.env["deployfleet.mobile.device"].sudo().browse(data["data"]["id"])
        self.assertEqual(device.user_id, self.user)
        self.assertEqual(device.platform, "android")

    def test_register_missing_platform_is_rejected(self):
        self.authenticate("push_user@example.com", "Test1234!")
        response = self.url_open("/api/mobile/push/register", data={"push_token": "tok"})
        data = json.loads(response.content)
        self.assertFalse(data["success"])


@tagged("post_install", "-at_install")
class TestDeployfleetMobilePushBridgeHandler(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Push Bridge Customer"})
        self.customer_user = self.env["res.users"].create({
            "name": "Push Bridge Customer User", "login": "push_bridge_customer@example.com",
            "email": "push_bridge_customer@example.com", "partner_id": self.customer.id,
        })
        self.device = self.env["deployfleet.mobile.device"].create({
            "user_id": self.customer_user.id, "push_token": "ExponentPushToken[xyz]", "platform": "ios",
        })
        pickup = self.env["deployfleet.depot"].create({"name": "Bridge Pickup"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Bridge Dropoff"})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id, "pickup_depot_id": pickup.id,
            "dropoff_depot_id": dropoff.id, "weight_kg": 300.0,
        })

    def test_delivery_completed_sends_push_to_customer_device(self):
        with patch(
            "odoo.addons.deployfleet_mobile_push_bridge.models.deployfleet_mobile_push_bridge.requests"
        ) as mock_requests:
            mock_requests.post.return_value = MagicMock()
            self.env["deployfleet.mobile.push.bridge"]._handle_bus_event(
                "deployfleet.delivery.completed", "deployfleet.shipment", self.shipment.id, {}
            )
            mock_requests.post.assert_called_once()
            call_kwargs = mock_requests.post.call_args.kwargs
            self.assertEqual(call_kwargs["json"]["to"], "ExponentPushToken[xyz]")

    def test_unrelated_event_sends_no_push(self):
        with patch(
            "odoo.addons.deployfleet_mobile_push_bridge.models.deployfleet_mobile_push_bridge.requests"
        ) as mock_requests:
            self.env["deployfleet.mobile.push.bridge"]._handle_bus_event(
                "deployfleet.invoice.confirmed", "deployfleet.invoice", 1, {}
            )
            mock_requests.post.assert_not_called()
