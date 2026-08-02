from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAIPermissions(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["deployfleet.ai.config"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.config.write({"deepseek_api_key": "test-key"})
        cls.feature = cls.env["deployfleet.ai.feature"].create({
            "key": "permissions_test_feature",
            "name": "Permissions Test Feature",
            "enabled": True,
            "model_tier": "cheap",
            "data_category": "general",
        })
        cls.manager_group = cls.env.ref("deployfleet_security.group_deployfleet_manager")
        cls.driver_group = cls.env.ref("deployfleet_security.group_deployfleet_driver")

    def _mock_provider_call(self):
        return patch.object(
            type(self.env["deployfleet.ai.core"]),
            "_call_provider",
            return_value=("mocked response", 10, 20),
        )

    def test_no_permission_rows_allows_any_user(self):
        # Should not raise — feature has no permission rows configured yet.
        self.env["deployfleet.ai.permission"]._check_user_allowed(self.env.user, self.feature.key)

    def test_permission_row_restricts_to_listed_group(self):
        self.env["deployfleet.ai.permission"].create({
            "feature_id": self.feature.id, "group_id": self.manager_group.id,
        })
        driver_only_user = self.env["res.users"].create({
            "name": "Driver Only", "login": "driver_only@example.com", "email": "driver_only@example.com",
            "groups_id": [(6, 0, [self.driver_group.id])],
        })
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.permission"]._check_user_allowed(driver_only_user, self.feature.key)

    def test_permission_row_allows_listed_group_member(self):
        self.env["deployfleet.ai.permission"].create({
            "feature_id": self.feature.id, "group_id": self.manager_group.id,
        })
        manager_user = self.env["res.users"].create({
            "name": "Manager User", "login": "manager_user@example.com", "email": "manager_user@example.com",
            "groups_id": [(6, 0, [self.manager_group.id])],
        })
        # Should not raise.
        self.env["deployfleet.ai.permission"]._check_user_allowed(manager_user, self.feature.key)

    def test_complete_blocks_before_calling_provider_when_not_permitted(self):
        self.env["deployfleet.ai.permission"].create({
            "feature_id": self.feature.id, "group_id": self.manager_group.id,
        })
        driver_only_user = self.env["res.users"].create({
            "name": "Driver Only 2", "login": "driver_only_2@example.com", "email": "driver_only_2@example.com",
            "groups_id": [(6, 0, [self.driver_group.id])],
        })
        with self._mock_provider_call() as mocked_provider:
            with self.assertRaises(UserError):
                self.env["deployfleet.ai.core"].with_user(driver_only_user).complete(
                    self.feature.key, "sys", "hello"
                )
            mocked_provider.assert_not_called()
