import json

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAIActionRequestBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.feature = cls.env["deployfleet.ai.feature"].create({
            "key": "actions_test_feature", "name": "Actions Test Feature", "enabled": True,
        })
        cls.manager_group = cls.env.ref("deployfleet_security.group_deployfleet_manager")
        cls.dispatcher_group = cls.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        cls.manager_user = cls.env["res.users"].create({
            "name": "AI Actions Manager", "login": "ai_actions_manager@example.com",
            "email": "ai_actions_manager@example.com",
            "group_ids": [(6, 0, [cls.manager_group.id])],
        })
        cls.dispatcher_user = cls.env["res.users"].create({
            "name": "AI Actions Dispatcher", "login": "ai_actions_dispatcher@example.com",
            "email": "ai_actions_dispatcher@example.com",
            "group_ids": [(6, 0, [cls.dispatcher_group.id])],
        })

    def _create_request(self, **extra):
        vals = {
            "feature_id": self.feature.id,
            "action_type": "create_vehicle_type",
            "target_model": "deployfleet.vehicle.type",
            "target_id": 0,
            "proposed_vals": json.dumps({"name": "AI Suggested Type", "code": "ai_suggested"}),
        }
        vals.update(extra)
        return self.env["deployfleet.ai.action.request"].create(vals)


class TestDeployfleetAIActionPipeline(TestDeployfleetAIActionRequestBase):
    def test_full_pipeline_happy_path(self):
        request = self._create_request()
        request.action_submit_for_approval()
        self.assertEqual(request.state, "pending_approval")

        request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "executed")
        self.assertEqual(request.approved_by, self.manager_user)
        self.assertTrue(request.executed_at)
        self.assertTrue(request.result_record_id)

        created = self.env["deployfleet.vehicle.type"].browse(request.result_record_id)
        self.assertEqual(created.name, "AI Suggested Type")
        self.assertEqual(created.code, "ai_suggested")

    def test_write_to_existing_record(self):
        vehicle_type = self.env["deployfleet.vehicle.type"].create({"name": "Original"})
        request = self._create_request(
            action_type="rename_vehicle_type",
            target_id=vehicle_type.id,
            proposed_vals=json.dumps({"name": "Renamed By AI"}),
        )
        request.action_submit_for_approval()
        request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "executed")
        self.assertEqual(vehicle_type.name, "Renamed By AI")

    def test_cannot_approve_a_draft_request(self):
        request = self._create_request()
        with self.assertRaises(UserError):
            request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "draft")

    def test_non_manager_cannot_approve(self):
        request = self._create_request()
        request.action_submit_for_approval()
        with self.assertRaises(UserError):
            request.with_user(self.dispatcher_user).action_approve()
        self.assertEqual(request.state, "pending_approval")

    def test_reject_sets_state_and_reason(self):
        request = self._create_request()
        request.action_submit_for_approval()
        request.with_user(self.manager_user).action_reject(reason="Not needed")
        self.assertEqual(request.state, "rejected")
        self.assertEqual(request.rejection_reason, "Not needed")

    def test_direct_execute_without_approval_raises(self):
        request = self._create_request()
        request.action_submit_for_approval()
        with self.assertRaises(UserError):
            request._execute()
        self.assertEqual(request.state, "pending_approval")

    def test_execute_failure_is_recorded_not_raised(self):
        request = self._create_request(
            proposed_vals=json.dumps({"nonexistent_field_xyz": "boom"}),
        )
        request.action_submit_for_approval()
        request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "failed")
        self.assertTrue(request.error_message)

    def test_forbidden_target_model_is_rejected_at_creation(self):
        with self.assertRaises(UserError):
            self._create_request(target_model="res.users", proposed_vals=json.dumps({"name": "Hacked"}))
