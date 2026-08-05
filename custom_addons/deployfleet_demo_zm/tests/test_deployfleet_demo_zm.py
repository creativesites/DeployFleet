import re

from odoo.tests import HttpCase, tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestDeployfleetDemoZm(TransactionCase):
    """Asserts against the dataset `post_init_hook` already generated at
    install time - does NOT call the hook again here. Several of its
    records (e.g. `deployfleet.ai.whatsapp.config`, unique per company)
    would violate their own SQL constraints on a second run, the same way
    installing this module twice on one database would."""

    def test_company_renamed_to_creativesites_logistics(self):
        company = self.env.ref("base.main_company")
        self.assertEqual(company.name, "CreativeSites Logistics")
        self.assertEqual(company.currency_id.name, "ZMW")

    def test_depots_created(self):
        self.assertGreaterEqual(self.env["deployfleet.depot"].search_count([]), 5)

    def test_vehicles_created_with_zambian_plates(self):
        vehicles = self.env["deployfleet.vehicle"].search([("license_plate", "like", "ABT 22%")])
        self.assertGreaterEqual(len(vehicles), 8)

    def test_drivers_created(self):
        driver_count = self.env["hr.employee"].search_count([("deployfleet_is_driver", "=", True)])
        self.assertGreaterEqual(driver_count, 7)

    def test_completed_shipments_generated_invoices(self):
        self.assertGreaterEqual(self.env["deployfleet.invoice"].search_count([]), 5)

    def test_fuel_anomaly_detected(self):
        self.assertTrue(self.env["deployfleet.fuel.anomaly"].search([]))

    def test_maintenance_predictions_computed(self):
        self.assertTrue(self.env["deployfleet.maintenance.prediction"].search([]))

    def test_financial_forecast_computed(self):
        self.assertTrue(self.env["deployfleet.financial.forecast"].search([]))

    def test_ai_action_requests_in_different_states(self):
        states = set(self.env["deployfleet.ai.action.request"].search([]).mapped("state"))
        self.assertIn("executed", states)
        self.assertIn("pending_approval", states)
        self.assertIn("rejected", states)

    def test_compliance_override_log_created_for_expired_vehicle(self):
        self.assertTrue(self.env["deployfleet.dispatch.compliance.override.log"].search([]))

    def test_breakdown_vehicle_has_breakdown_status(self):
        vehicle = self.env["deployfleet.vehicle"].search([("license_plate", "=", "ABT 2207")], limit=1)
        self.assertEqual(vehicle.status, "breakdown")

    def test_demo_login_enabled_flag_set(self):
        icp = self.env["ir.config_parameter"].sudo()
        self.assertEqual(icp.get_param("deployfleet_demo_zm.demo_login_enabled"), "True")

    def test_demo_login_users_created_in_correct_groups(self):
        expected_groups = {
            "demo.owner@deployfleet.demo": "deployfleet_security.group_deployfleet_owner",
            "demo.dispatcher@deployfleet.demo": "deployfleet_security.group_deployfleet_dispatcher",
            "demo.driver@deployfleet.demo": "deployfleet_security.group_deployfleet_driver",
        }
        for login, group_xmlid in expected_groups.items():
            user = self.env["res.users"].search([("login", "=", login)], limit=1)
            self.assertTrue(user, f"expected a demo user with login {login!r}")
            self.assertIn(self.env.ref(group_xmlid), user.group_ids)

    def test_demo_driver_login_linked_to_a_real_driver_employee(self):
        user = self.env["res.users"].search([("login", "=", "demo.driver@deployfleet.demo")], limit=1)
        employee = self.env["hr.employee"].search([("user_id", "=", user.id)], limit=1)
        self.assertTrue(employee)
        self.assertTrue(employee.deployfleet_is_driver)

    def test_demo_customer_login_scoped_under_a_real_customer_company(self):
        user = self.env["res.users"].search([("login", "=", "demo.customer@deployfleet.demo")], limit=1)
        self.assertTrue(user)
        self.assertIn(self.env.ref("base.group_portal"), user.group_ids)
        self.assertEqual(user.partner_id.commercial_partner_id.name, "Kwacha Traders Ltd")

    def test_demo_login_passwords_stored_only_in_config_parameter(self):
        icp = self.env["ir.config_parameter"].sudo()
        for role in ("owner", "dispatcher", "driver", "customer"):
            password = icp.get_param(f"deployfleet_demo_zm.demo_login_password_{role}")
            self.assertTrue(password)
            self.assertGreater(len(password), 20)


@tagged("post_install", "-at_install")
class TestDeployfleetDemoLoginController(HttpCase):
    """HTTP-level tests for the one-click demo-login controller
    deployfleet_ui's redesigned login page posts to. Relies on the
    dataset the class-level post_init_hook already generated (this
    class's own setUp does not re-run it, same discipline as
    TestDeployfleetDemoZm above).

    The route is a genuine csrf=True browser-form POST (matching how
    Odoo's own /web/login protects itself), so every test here first
    pulls a real csrf_token off a rendered /web/login page, the same
    way an actual browser session would, rather than disabling CSRF for
    the test."""

    def _csrf_token(self):
        # QWeb's t-att-value directive on the csrf_token input compiles
        # down to a plain `value="..."` attribute in the rendered HTML -
        # this is what an actual browser session sees and submits back.
        html = self.url_open("/web/login").text
        match = re.search(r'name="csrf_token"[^>]*\bvalue="([^"]+)"', html)
        self.assertTrue(match, "could not find a csrf_token on /web/login")
        return match.group(1)

    def test_demo_login_authenticates_and_redirects(self):
        response = self.url_open(
            "/web/login/demo/owner", data={"csrf_token": self._csrf_token()}, allow_redirects=False
        )
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers.get("Location"), "/odoo")

    def test_demo_login_unknown_role_returns_404(self):
        response = self.url_open(
            "/web/login/demo/not-a-real-role", data={"csrf_token": self._csrf_token()}
        )
        self.assertEqual(response.status_code, 404)

    def test_demo_login_get_not_allowed(self):
        # POST-only route (deliberately - see demo_login.py's own comment
        # on why a login action must not be GET-triggerable); a matched
        # path hit with the wrong method is a 405, not a 404.
        response = self.url_open("/web/login/demo/owner")
        self.assertEqual(response.status_code, 405)

    def test_demo_login_returns_404_when_disabled(self):
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("deployfleet_demo_zm.demo_login_enabled", "False")
        try:
            response = self.url_open(
                "/web/login/demo/owner", data={"csrf_token": self._csrf_token()}
            )
            self.assertEqual(response.status_code, 404)
        finally:
            icp.set_param("deployfleet_demo_zm.demo_login_enabled", "True")
