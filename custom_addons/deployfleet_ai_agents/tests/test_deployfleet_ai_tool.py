from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

_EXPECTED_TOOL_KEYS = {
    "get_vehicle_summary", "get_due_maintenance", "get_available_drivers",
    "get_unassigned_shipments", "get_expiring_documents", "mark_vehicle_available",
}


@tagged("post_install", "-at_install")
class TestDeployfleetAITool(TransactionCase):
    """Regression tests for the Phase 1b tool registry (docs/architecture/
    21-copilot-rail-architecture.md §3) — fixed dict-dispatch execution,
    per-agent tool scoping, and the constraint keeping a tool record from
    naming a key this module doesn't actually implement."""

    def test_expected_tools_seeded(self):
        tools = self.env["deployfleet.ai.tool"].search([])
        self.assertEqual(set(tools.mapped("key")), _EXPECTED_TOOL_KEYS)

    def test_finance_and_customer_agents_have_no_tools(self):
        finance_agent = self.env.ref("deployfleet_ai_agents.agent_finance_agent")
        customer_agent = self.env.ref("deployfleet_ai_agents.agent_customer_agent")
        self.assertFalse(self.env["deployfleet.ai.tool"].schemas_for_agent(finance_agent))
        self.assertFalse(self.env["deployfleet.ai.tool"].schemas_for_agent(customer_agent))

    def test_to_llm_schema_shape(self):
        tool = self.env.ref("deployfleet_ai_agents.tool_get_vehicle_summary")
        schema = tool.to_llm_schema()
        self.assertEqual(schema["name"], "get_vehicle_summary")
        self.assertIn("description", schema)
        self.assertEqual(schema["parameters"]["type"], "object")

    def test_execute_unassigned_shipments_returns_a_count_not_an_error(self):
        tool = self.env.ref("deployfleet_ai_agents.tool_get_unassigned_shipments")
        result = tool.execute({})
        self.assertNotIn("error", result)
        self.assertIn("count", result)

    def test_execute_unknown_key_never_raises(self):
        tool = self.env.ref("deployfleet_ai_agents.tool_get_vehicle_summary")
        # A tool missing its own vehicle_id argument should degrade to an
        # {"error": ...} dict, never an exception escaping to the caller.
        result = tool.execute({})
        self.assertIn("error", result)

    def test_key_must_have_a_registered_handler(self):
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.tool"].create({
                "key": "not_a_real_handler",
                "name": "Bogus Tool",
                "description": "This key has no _TOOL_HANDLERS entry.",
            })

    def test_build_executor_refuses_tool_outside_agent_scope(self):
        compliance_agent = self.env.ref("deployfleet_ai_agents.agent_compliance_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(compliance_agent)
        # Compliance Agent only has get_expiring_documents (§3/§10) — a
        # tool-call for another agent's tool must be refused, not silently run.
        result = executor("get_vehicle_summary", {"vehicle_id": 1})
        self.assertIn("error", result)

    def test_build_executor_runs_tool_within_agent_scope(self):
        compliance_agent = self.env.ref("deployfleet_ai_agents.agent_compliance_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(compliance_agent)
        result = executor("get_expiring_documents", {})
        self.assertNotIn("error", result)
        self.assertIn("count", result)


@tagged("post_install", "-at_install")
class TestDeployfleetAIChatSessionToolCalling(TransactionCase):
    """Regression tests for the _get_reply() override that routes chat
    turns through complete_with_tools() when the session's feature maps
    to an agent with registered tools (doc 21 §3/§10 Phase 1b)."""

    def _create_session(self, feature):
        return self.env["deployfleet.ai.chat.session"].create({
            "name": "Test Chat", "feature_id": feature.id, "system_prompt": "sys",
        })

    def test_session_for_agent_with_tools_routes_through_complete_with_tools(self):
        agent = self.env.ref("deployfleet_ai_agents.agent_fleet_analyst")
        session = self._create_session(agent.feature_id)
        with patch.object(
            type(self.env["deployfleet.ai.core"]), "complete_with_tools", return_value="tool-informed reply",
        ) as mocked:
            reply = session.action_send_message("how's vehicle 1?")
        self.assertEqual(reply, "tool-informed reply")
        mocked.assert_called_once()
        _feature_key, _system_prompt, _transcript, tools = mocked.call_args.args
        self.assertTrue(any(tool["name"] == "get_vehicle_summary" for tool in tools))

    def test_session_for_feature_without_agent_falls_back_to_plain_complete(self):
        feature = self.env["deployfleet.ai.feature"].create({
            "key": "no_agent_feature", "name": "No Agent Feature",
            "enabled": True, "model_tier": "cheap", "data_category": "general",
        })
        session = self._create_session(feature)
        with patch.object(
            type(self.env["deployfleet.ai.core"]), "complete", return_value="plain reply",
        ) as mocked_complete, patch.object(
            type(self.env["deployfleet.ai.core"]), "complete_with_tools",
        ) as mocked_complete_with_tools:
            reply = session.action_send_message("hello")
        self.assertEqual(reply, "plain reply")
        mocked_complete.assert_called_once()
        mocked_complete_with_tools.assert_not_called()

    def test_session_for_agent_with_tools_persists_tool_call_transparency(self):
        """doc 21 §5's tool_calls field: the _get_reply() override passes a
        tool_call_log list into complete_with_tools() by reference, so a
        provider adapter that actually invokes a tool (simulated here via
        the mock's side_effect, since complete_with_tools() itself is
        mocked) leaves a record action_send_message() can persist."""
        agent = self.env.ref("deployfleet_ai_agents.agent_fleet_analyst")
        session = self._create_session(agent.feature_id)

        def fake_complete_with_tools(_feature_key, _system_prompt, _transcript, _tools,
                                      executor=None, tool_call_log=None, company=None):
            del executor, company  # unused - only tool_call_log matters for this test
            if tool_call_log is not None:
                tool_call_log.append({"tool": "get_vehicle_summary", "args": {"vehicle_id": 1}})
            return "vehicle 1 is available"

        with patch.object(
            type(self.env["deployfleet.ai.core"]), "complete_with_tools", side_effect=fake_complete_with_tools,
        ):
            session.action_send_message("how's vehicle 1?")

        message = session.message_ids.filtered(lambda m: m.role == "assistant")
        self.assertTrue(message.tool_calls)
        self.assertIn("get_vehicle_summary", message.tool_calls)


@tagged("post_install", "-at_install")
class TestDeployfleetAIMarkVehicleAvailableTool(TransactionCase):
    """Regression tests for the first write tool (doc 21 §3/§4/§10 Phase
    3) — every call still goes through deployfleet.ai.action.request.
    propose(), never a direct write; the seeded
    auto_exec_mark_vehicle_available allow-list entry (deployfleet_ai_actions)
    means this specific tool auto-executes in practice, exercised here
    end to end rather than mocked."""

    def _vehicle(self, plate):
        return self.env["deployfleet.vehicle"].create({
            "license_plate": plate,
            "vehicle_type_id": self.env["deployfleet.vehicle.type"].create({"name": f"Type {plate}"}).id,
        })

    def test_tool_proposes_and_auto_executes_via_seeded_allow_list(self):
        vehicle = self._vehicle("TOOL-EXEC-1")
        vehicle.status = "maintenance"
        agent = self.env.ref("deployfleet_ai_agents.agent_dispatch_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(agent)
        result = executor("mark_vehicle_available", {"vehicle_id": vehicle.id})
        self.assertEqual(result["status"], "executed")
        self.assertEqual(vehicle.status, "available")

        request = self.env["deployfleet.ai.action.request"].search(
            [("target_model", "=", "deployfleet.vehicle"), ("target_id", "=", vehicle.id)], limit=1,
        )
        self.assertTrue(request.auto_executed)
        self.assertEqual(request.feature_id.key, "dispatch_agent")

    def test_tool_requires_vehicle_id(self):
        agent = self.env.ref("deployfleet_ai_agents.agent_dispatch_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(agent)
        result = executor("mark_vehicle_available", {})
        self.assertIn("error", result)

    def test_tool_reports_unknown_vehicle(self):
        agent = self.env.ref("deployfleet_ai_agents.agent_dispatch_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(agent)
        result = executor("mark_vehicle_available", {"vehicle_id": 999999})
        self.assertIn("error", result)

    def test_tool_not_available_to_other_agents(self):
        compliance_agent = self.env.ref("deployfleet_ai_agents.agent_compliance_agent")
        executor = self.env["deployfleet.ai.tool"].build_executor(compliance_agent)
        result = executor("mark_vehicle_available", {"vehicle_id": 1})
        self.assertIn("error", result)


@tagged("post_install", "-at_install")
class TestDeployfleetAIGetVehicleSummaryToolCache(TransactionCase):
    """Regression tests for get_vehicle_summary's use of
    deployfleet.ai.entity.summary (doc 21 §6 - deployfleet_ai_core) - the
    one real consumer of that cache."""

    def _vehicle(self, plate):
        return self.env["deployfleet.vehicle"].create({
            "license_plate": plate,
            "vehicle_type_id": self.env["deployfleet.vehicle.type"].create({"name": f"Type {plate}"}).id,
        })

    def _executor(self):
        agent = self.env.ref("deployfleet_ai_agents.agent_fleet_analyst")
        return self.env["deployfleet.ai.tool"].build_executor(agent)

    def test_first_call_populates_the_cache(self):
        vehicle = self._vehicle("CACHE-1")
        executor = self._executor()
        result = executor("get_vehicle_summary", {"vehicle_id": vehicle.id})
        self.assertIn("summary", result)
        cached = self.env["deployfleet.ai.entity.summary"].get_cached("deployfleet.vehicle", vehicle.id)
        self.assertTrue(cached)
        self.assertEqual(cached.summary_text, result["summary"])

    def test_second_call_with_no_change_serves_the_cached_text(self):
        """Manually corrupts the cached summary_text, then confirms an
        unchanged vehicle's second tool call returns the (now-wrong)
        cached text rather than recomputing - proving the signature
        check actually short-circuits recomputation, not just that the
        cache exists."""
        vehicle = self._vehicle("CACHE-2")
        executor = self._executor()
        executor("get_vehicle_summary", {"vehicle_id": vehicle.id})
        cached = self.env["deployfleet.ai.entity.summary"].get_cached("deployfleet.vehicle", vehicle.id)
        cached.summary_text = "DELIBERATELY STALE MARKER"

        result = executor("get_vehicle_summary", {"vehicle_id": vehicle.id})
        self.assertEqual(result["summary"], "DELIBERATELY STALE MARKER")

    def test_status_change_invalidates_and_recomputes(self):
        vehicle = self._vehicle("CACHE-3")
        executor = self._executor()
        first = executor("get_vehicle_summary", {"vehicle_id": vehicle.id})
        vehicle.status = "maintenance"
        second = executor("get_vehicle_summary", {"vehicle_id": vehicle.id})
        self.assertNotEqual(first["summary"], second["summary"])
        self.assertIn("maintenance", second["summary"])
