import json

from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetMobileDispatcherController(HttpCase):
    def setUp(self):
        super().setUp()
        self.dispatcher_user = self.env["res.users"].create({
            "name": "Mobile Dispatcher",
            "login": "mobile_dispatcher@example.com",
            "email": "mobile_dispatcher@example.com",
            "password": "Test1234!",
            "group_ids": [(4, self.env.ref("deployfleet_security.group_deployfleet_dispatcher").id)],
        })

    def test_dashboard_denied_without_dispatcher_group(self):
        self.authenticate(None, None)
        response = self.url_open("/api/mobile/dispatcher/dashboard")
        data = json.loads(response.content)
        self.assertFalse(data["success"])

    def test_dashboard_returns_counts_for_dispatcher(self):
        self.authenticate("mobile_dispatcher@example.com", "Test1234!")
        response = self.url_open("/api/mobile/dispatcher/dashboard")
        data = json.loads(response.content)
        self.assertTrue(data["success"])
        for key in ("active_trips", "pending_shipments", "vehicles_available", "vehicles_assigned"):
            self.assertIn(key, data["data"])

    def test_confirm_nonexistent_assignment_returns_error(self):
        self.authenticate("mobile_dispatcher@example.com", "Test1234!")
        response = self.url_open("/api/mobile/dispatcher/assignments/999999/confirm", data={})
        data = json.loads(response.content)
        self.assertFalse(data["success"])
