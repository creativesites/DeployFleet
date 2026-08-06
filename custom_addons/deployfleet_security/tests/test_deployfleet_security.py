from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetSecurityGroups(TransactionCase):
    def test_manager_implies_dispatcher_and_driver(self):
        driver = self.env.ref("deployfleet_security.group_deployfleet_driver")
        dispatcher = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        manager = self.env.ref("deployfleet_security.group_deployfleet_manager")
        owner = self.env.ref("deployfleet_security.group_deployfleet_owner")

        self.assertIn(driver, dispatcher.implied_ids)
        self.assertIn(dispatcher, manager.implied_ids)
        self.assertIn(manager, owner.implied_ids)

    def test_user_in_manager_group_gets_driver_access_too(self):
        manager = self.env.ref("deployfleet_security.group_deployfleet_manager")
        driver = self.env.ref("deployfleet_security.group_deployfleet_driver")
        user = self.env["res.users"].create({
            "name": "Test Fleet Manager",
            "login": "test_fleet_manager@example.com",
            "group_ids": [(6, 0, [manager.id])],
        })
        self.assertIn(driver, user.group_ids)

    def test_owner_implies_payroll_officer_and_system_auditor(self):
        owner = self.env.ref("deployfleet_security.group_deployfleet_owner")
        payroll_officer = self.env.ref("deployfleet_security.group_deployfleet_hr_payroll_officer")
        system_auditor = self.env.ref("deployfleet_security.group_deployfleet_system_auditor")
        self.assertIn(payroll_officer, owner.implied_ids)
        self.assertIn(system_auditor, owner.implied_ids)

    def test_user_in_owner_group_gets_payroll_and_audit_access_too(self):
        owner = self.env.ref("deployfleet_security.group_deployfleet_owner")
        payroll_officer = self.env.ref("deployfleet_security.group_deployfleet_hr_payroll_officer")
        system_auditor = self.env.ref("deployfleet_security.group_deployfleet_system_auditor")
        user = self.env["res.users"].create({
            "name": "Test Owner",
            "login": "test_owner@example.com",
            "group_ids": [(6, 0, [owner.id])],
        })
        self.assertIn(payroll_officer, user.group_ids)
        self.assertIn(system_auditor, user.group_ids)

    def test_manager_does_not_get_payroll_access(self):
        manager = self.env.ref("deployfleet_security.group_deployfleet_manager")
        payroll_officer = self.env.ref("deployfleet_security.group_deployfleet_hr_payroll_officer")
        user = self.env["res.users"].create({
            "name": "Test Manager Only",
            "login": "test_manager_only@example.com",
            "group_ids": [(6, 0, [manager.id])],
        })
        self.assertNotIn(payroll_officer, user.group_ids)

    def test_driver_implies_base_group_user(self):
        # Found live (Aug 2026): a real dispatcher/driver-only login hit a
        # 403 on res.partner, since neither group had any path to Odoo's
        # own "Internal User" baseline - only owner did, transitively,
        # through its owner-only hr_payroll_officer/system_auditor grants.
        # Fixed at the base of the chain so driver/dispatcher/manager all
        # inherit it, matching the pattern hr.group_hr_user already uses
        # in real Odoo core.
        driver = self.env.ref("deployfleet_security.group_deployfleet_driver")
        self.assertIn(self.env.ref("base.group_user"), driver.implied_ids)

    def test_user_in_driver_group_can_read_res_partner(self):
        driver = self.env.ref("deployfleet_security.group_deployfleet_driver")
        user = self.env["res.users"].create({
            "name": "Test Driver Only",
            "login": "test_driver_only@example.com",
            "group_ids": [(6, 0, [driver.id])],
        })
        self.assertIn(self.env.ref("base.group_user"), user.group_ids)
        # The actual real-world failure mode, not just a group-membership
        # check: this raised AccessError before the fix.
        self.env["res.partner"].with_user(user).search([], limit=1)


@tagged("post_install", "-at_install")
class TestDeployfleetLicense(TransactionCase):
    def test_activate_sets_active_state(self):
        record = self.env["deployfleet.license"].create({
            "license_key": "TEST-KEY-001",
            "valid_until": fields.Date.today() + timedelta(days=30),
        })
        record.action_activate()
        self.assertEqual(record.state, "active")
        self.assertTrue(record.is_valid())
        self.assertTrue(record.log_ids)

    def test_activate_past_valid_until_marks_expired(self):
        record = self.env["deployfleet.license"].create({
            "license_key": "TEST-KEY-002",
            "valid_until": fields.Date.today() - timedelta(days=1),
        })
        record.action_activate()
        self.assertEqual(record.state, "expired")
        self.assertFalse(record.is_valid())

    def test_invalidate(self):
        record = self.env["deployfleet.license"].create({"license_key": "TEST-KEY-003"})
        record.action_activate()
        record.action_invalidate(reason="Test revocation")
        self.assertEqual(record.state, "invalid")
        self.assertFalse(record.is_valid())

    def test_cron_expires_stale_active_license(self):
        record = self.env["deployfleet.license"].create({
            "license_key": "TEST-KEY-004",
            "state": "active",
            "valid_until": fields.Date.today() - timedelta(days=5),
        })
        expired = self.env["deployfleet.license"]._cron_check_expiry()
        self.assertIn(record, expired)
        self.assertEqual(record.state, "expired")
