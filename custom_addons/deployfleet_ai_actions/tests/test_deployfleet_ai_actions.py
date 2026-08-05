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
        cls.auditor_group = cls.env.ref("deployfleet_security.group_deployfleet_system_auditor")
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
        cls.auditor_user = cls.env["res.users"].create({
            "name": "AI Actions Auditor", "login": "ai_actions_auditor@example.com",
            "email": "ai_actions_auditor@example.com",
            "group_ids": [(6, 0, [cls.auditor_group.id])],
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

    def test_dispatcher_can_submit_own_draft_request(self):
        """Regression test for the dispatcher write=0 ACL bug (same class
        as the previously-fixed deployfleet.leave.request gap): a
        dispatcher could create a draft but never call
        action_submit_for_approval() on it, since that's a write."""
        request = self._create_request().with_user(self.dispatcher_user)
        request.action_submit_for_approval()
        self.assertEqual(request.state, "pending_approval")

    def test_non_manager_cannot_reject(self):
        request = self._create_request()
        request.action_submit_for_approval()
        with self.assertRaises(UserError):
            request.with_user(self.dispatcher_user).action_reject(reason="No thanks")
        self.assertEqual(request.state, "pending_approval")

    def test_system_auditor_can_read_but_not_write(self):
        request = self._create_request()
        request.action_submit_for_approval()
        # Read access: the audit trail is exactly what this role exists to see.
        self.assertEqual(request.with_user(self.auditor_user).state, "pending_approval")
        with self.assertRaises(UserError):
            request.with_user(self.auditor_user).action_approve()


class TestDeployfleetAIActionMethodExecution(TestDeployfleetAIActionRequestBase):
    """Regression tests for _execute()'s action_method branch (doc 21
    §3/§4/§10 Phase 3) - the concrete lever most real dispatch/fleet
    actions actually are, not a field write. deployfleet.vehicle.
    action_set_available() is a real zero-arg state-transition method,
    already reused as the safe test target the same way the pipeline
    tests above reuse deployfleet.vehicle.type."""

    def test_action_method_call_executes_and_records_result(self):
        # mark_vehicle_available/action_set_available is seeded as an
        # allow-list entry by deployfleet_ai_actions' own demo data, so
        # this exercises the normal (non-test-registered) path.
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "AI-EXEC-1", "vehicle_type_id": self._vehicle_type().id,
        })
        vehicle.status = "maintenance"
        request = self._create_request(
            action_type="mark_vehicle_available", target_model="deployfleet.vehicle",
            target_id=vehicle.id, proposed_vals=json.dumps({}), action_method="action_set_available",
        )
        request.action_submit_for_approval()
        request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "executed")
        self.assertEqual(request.result_record_id, vehicle.id)
        self.assertEqual(vehicle.status, "available")

    def test_action_method_not_on_the_allow_list_cannot_be_approved(self):
        """Regression test for an engineering-audit finding: an
        action_method request previously had no gate beyond the small,
        business-model-free forbidden-model deny-list - any producer
        could set action_method to an arbitrary action_*-prefixed method
        on any non-forbidden model, and a manager clicking Approve would
        execute it exactly as approved, with no allow-list check at all."""
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "AI-EXEC-4", "vehicle_type_id": self._vehicle_type().id,
        })
        request = self._create_request(
            action_type="some_other_action", target_model="deployfleet.vehicle",
            target_id=vehicle.id, proposed_vals=json.dumps({}), action_method="action_set_maintenance",
        )
        request.action_submit_for_approval()
        with self.assertRaises(UserError):
            request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "pending_approval")

    def test_action_method_allow_listed_but_not_auto_execute_still_requires_manual_approval(self):
        """auto_execute is a narrower flag *within* the broader allow-
        list, not a synonym for it - an entry with auto_execute=False
        may still be manually approved (it's on the allow-list) but must
        never bypass the approval queue on its own."""
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "AI-EXEC-5", "vehicle_type_id": self._vehicle_type().id,
        })
        vehicle.status = "maintenance"
        self.env["deployfleet.ai.auto.executable.action"].create({
            "action_type": "mark_vehicle_available_manual_only", "target_model": "deployfleet.vehicle",
            "action_method": "action_set_available", "auto_execute": False,
            "description": "Test allow-list entry, manual-approval-only.",
        })
        request = self.env["deployfleet.ai.action.request"].propose(
            feature_key=self.feature.key, action_type="mark_vehicle_available_manual_only",
            target_model="deployfleet.vehicle", target_id=vehicle.id, proposed_vals={},
            action_method="action_set_available",
        )
        self.assertEqual(request.state, "pending_approval")
        self.assertFalse(request.auto_executed)
        self.assertEqual(vehicle.status, "maintenance", "no write should have happened yet")

        request.with_user(self.manager_user).action_approve()
        self.assertEqual(request.state, "executed")
        self.assertEqual(vehicle.status, "available")

    def test_action_method_must_start_with_action_prefix(self):
        with self.assertRaises(UserError):
            self._create_request(
                action_type="mark_vehicle_available", target_model="deployfleet.vehicle",
                target_id=1, proposed_vals=json.dumps({}), action_method="set_available",
            )

    def test_action_method_requires_a_target_id(self):
        with self.assertRaises(UserError):
            self._create_request(
                action_type="mark_vehicle_available", target_model="deployfleet.vehicle",
                target_id=0, proposed_vals=json.dumps({}), action_method="action_set_available",
            )

    def _vehicle_type(self):
        return self.env["deployfleet.vehicle.type"].create({"name": "AI Actions Test Type"})


class TestDeployfleetAIActionPropose(TestDeployfleetAIActionRequestBase):
    """Regression tests for propose() and the auto-executable allow-list
    (doc 21 §4/§10 Phase 3)."""

    def test_propose_without_allow_list_match_stays_pending_approval(self):
        request = self.env["deployfleet.ai.action.request"].propose(
            feature_key=self.feature.key, action_type="rename_vehicle_type",
            target_model="deployfleet.vehicle.type", target_id=0,
            proposed_vals={"name": "Proposed Type"},
        )
        self.assertEqual(request.state, "pending_approval")
        self.assertFalse(request.auto_executed)
        self.assertFalse(request.approved_by)

    def test_propose_with_allow_list_match_auto_executes(self):
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "AI-EXEC-2",
            "vehicle_type_id": self.env["deployfleet.vehicle.type"].create({"name": "Auto Exec Type"}).id,
        })
        vehicle.status = "maintenance"
        self.env["deployfleet.ai.auto.executable.action"].create({
            "action_type": "mark_vehicle_available", "target_model": "deployfleet.vehicle",
            "action_method": "action_set_available", "description": "Test allow-list entry.",
        })
        request = self.env["deployfleet.ai.action.request"].propose(
            feature_key=self.feature.key, action_type="mark_vehicle_available",
            target_model="deployfleet.vehicle", target_id=vehicle.id, proposed_vals={},
            action_method="action_set_available",
        )
        self.assertEqual(request.state, "executed")
        self.assertTrue(request.auto_executed)
        self.assertFalse(request.approved_by, "auto-execution has no human approver")
        self.assertEqual(vehicle.status, "available")

    def test_payroll_data_category_never_auto_executes_even_with_allow_list_match(self):
        payroll_feature = self.env["deployfleet.ai.feature"].create({
            "key": "actions_test_payroll_feature", "name": "Payroll Test Feature",
            "enabled": True, "data_category": "payroll",
        })
        vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "AI-EXEC-3",
            "vehicle_type_id": self.env["deployfleet.vehicle.type"].create({"name": "Payroll Guard Type"}).id,
        })
        vehicle.status = "maintenance"
        self.env["deployfleet.ai.auto.executable.action"].create({
            "action_type": "mark_vehicle_available", "target_model": "deployfleet.vehicle",
            "action_method": "action_set_available", "description": "Test allow-list entry.",
        })
        request = self.env["deployfleet.ai.action.request"].propose(
            feature_key=payroll_feature.key, action_type="mark_vehicle_available",
            target_model="deployfleet.vehicle", target_id=vehicle.id, proposed_vals={},
            action_method="action_set_available",
        )
        self.assertEqual(request.state, "pending_approval")
        self.assertFalse(request.auto_executed)
        self.assertEqual(vehicle.status, "maintenance", "no write should have happened at all")

    def test_propose_raises_for_disabled_feature(self):
        self.feature.enabled = False
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.action.request"].propose(
                feature_key=self.feature.key, action_type="rename_vehicle_type",
                target_model="deployfleet.vehicle.type", target_id=0,
                proposed_vals={"name": "Should Not Be Created"},
            )
