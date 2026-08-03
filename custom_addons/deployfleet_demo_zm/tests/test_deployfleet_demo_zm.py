from odoo.tests.common import TransactionCase, tagged


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
