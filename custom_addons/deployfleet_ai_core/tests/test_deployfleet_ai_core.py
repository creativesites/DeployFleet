import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAICoreBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.policy = cls.env["deployfleet.ai.policy"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.config = cls.env["deployfleet.ai.config"].search([("company_id", "=", cls.env.company.id)], limit=1)
        cls.config.write({"deepseek_api_key": "test-key"})
        cls.feature = cls.env["deployfleet.ai.feature"].create({
            "key": "test_feature",
            "name": "Test Feature",
            "enabled": True,
            "model_tier": "cheap",
            "data_category": "general",
        })

    def _mock_provider_call(self, text="mocked response", tokens_in=10, tokens_out=20):
        return patch.object(
            type(self.env["deployfleet.ai.core"]),
            "_call_provider",
            return_value=(text, tokens_in, tokens_out),
        )


class TestDeployfleetAICoreAccessAsRealUser(TestDeployfleetAICoreBase):
    """Regression tests for the headline ACL bug found during the AI &
    Intelligence domain audit: deployfleet.ai.config/response.cache/
    usage were base.group_system-only, so complete() raised AccessError
    for every real DeployFleet role (owner/manager/dispatcher/driver —
    none of which imply base.group_system). Every test above this class
    runs as the default TransactionCase superuser env, which is why the
    bug was never caught by the existing suite. Fixed by sudo()-ing the
    router's own internal config/budget/cache/usage-log calls in
    deployfleet_ai_engine.py, rather than loosening the ACLs those
    models are deliberately locked down with (deployfleet.ai.config
    holds provider API keys)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        dispatcher_group = cls.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        cls.dispatcher_user = cls.env["res.users"].create({
            "name": "AI Core Dispatcher", "login": "ai_core_dispatcher@example.com",
            "email": "ai_core_dispatcher@example.com",
            "group_ids": [(6, 0, [dispatcher_group.id])],
        })

    def test_dispatcher_can_complete_a_call_end_to_end(self):
        with self._mock_provider_call(text="dispatcher-visible response"):
            result = self.env["deployfleet.ai.core"].with_user(self.dispatcher_user).complete(
                "test_feature", "sys", "hello",
            )
        self.assertEqual(result, "dispatcher-visible response")

        log = self.env["deployfleet.ai.usage"].search([("feature", "=", "test_feature")], limit=1)
        self.assertEqual(log.user_id, self.dispatcher_user)

    def test_dispatcher_second_identical_call_hits_cache(self):
        with self._mock_provider_call(text="cached for dispatcher") as mocked:
            self.env["deployfleet.ai.core"].with_user(self.dispatcher_user).complete("test_feature", "sys", "hello")
            self.assertEqual(mocked.call_count, 1)
        # Not mocked - would raise for lack of a real API key/network if the
        # dispatcher couldn't actually reach the response cache.
        result = self.env["deployfleet.ai.core"].with_user(self.dispatcher_user).complete(
            "test_feature", "sys", "hello",
        )
        self.assertEqual(result, "cached for dispatcher")

    def test_manager_can_toggle_feature_enabled(self):
        manager_group = self.env.ref("deployfleet_security.group_deployfleet_manager")
        manager_user = self.env["res.users"].create({
            "name": "AI Core Manager", "login": "ai_core_manager@example.com",
            "email": "ai_core_manager@example.com",
            "group_ids": [(6, 0, [manager_group.id])],
        })
        self.feature.with_user(manager_user).enabled = False
        self.assertFalse(self.feature.enabled)


class TestDeployfleetAIChatSession(TestDeployfleetAICoreBase):
    """Regression tests for the Copilot Rail's Chat tab persistence layer
    (docs/architecture/21-copilot-rail-architecture.md §5/§10 Phase 1) —
    deployfleet.ai.chat.session/.message were modeled since Phase 0 but
    had zero consumers until this."""

    def _create_session(self):
        return self.env["deployfleet.ai.chat.session"].create({
            "name": "Test Chat", "feature_id": self.feature.id, "system_prompt": "sys",
        })

    def test_send_message_persists_both_turns_and_returns_reply(self):
        session = self._create_session()
        with self._mock_provider_call(text="here is your answer"):
            reply = session.action_send_message("what's up?")
        self.assertEqual(reply, "here is your answer")
        self.assertEqual(len(session.message_ids), 2)
        self.assertEqual(session.message_ids[0].role, "user")
        self.assertEqual(session.message_ids[0].content, "what's up?")
        self.assertEqual(session.message_ids[1].role, "assistant")
        self.assertEqual(session.message_ids[1].content, "here is your answer")

    def test_second_message_includes_prior_turns_in_transcript(self):
        session = self._create_session()
        with self._mock_provider_call(text="first reply"):
            session.action_send_message("first question")
        with self._mock_provider_call(text="second reply") as mocked:
            session.action_send_message("second question")
        sent_args = " ".join(str(arg) for arg in mocked.call_args.args)
        self.assertIn("first question", sent_args)
        self.assertIn("first reply", sent_args)
        self.assertIn("second question", sent_args)

    def test_session_respects_feature_enabled_gate(self):
        session = self._create_session()
        self.feature.enabled = False
        with self.assertRaises(UserError):
            session.action_send_message("hello")

    def test_context_note_is_folded_into_transcript_but_never_persisted(self):
        session = self._create_session()
        with self._mock_provider_call(text="here's the vehicle status") as mocked:
            session.action_send_message("what's going on?", context_note="viewing vehicle ABC-123")
        sent_args = " ".join(str(arg) for arg in mocked.call_args.args)
        self.assertIn("viewing vehicle ABC-123", sent_args)
        # The context note must never leak into the persisted, user-visible
        # chat history - only the turn actually typed/heard is stored.
        self.assertNotIn("viewing vehicle ABC-123", session.message_ids[0].content)

    def test_rich_payload_block_is_extracted_and_stripped_from_content(self):
        session = self._create_session()
        raw_reply = (
            'Vehicle ZM-1234 looks fine.\n'
            '```json\n'
            '{"components": [{"type": "vehicle_card", "vehicle_id": 123}], "actions_available": []}\n'
            '```'
        )
        with self._mock_provider_call(text=raw_reply):
            reply = session.action_send_message("how's the vehicle?")
        self.assertEqual(reply, "Vehicle ZM-1234 looks fine.")
        message = session.message_ids.filtered(lambda m: m.role == "assistant")
        self.assertEqual(message.content, "Vehicle ZM-1234 looks fine.")
        self.assertNotIn("```", message.content)
        payload = json.loads(message.rich_payload)
        self.assertEqual(payload["components"], [{"type": "vehicle_card", "vehicle_id": 123}])

    def test_malformed_rich_payload_block_degrades_to_plain_text(self):
        session = self._create_session()
        raw_reply = 'Here you go.\n```json\n{not valid json\n```'
        with self._mock_provider_call(text=raw_reply):
            reply = session.action_send_message("hello")
        self.assertEqual(reply, raw_reply)
        message = session.message_ids.filtered(lambda m: m.role == "assistant")
        self.assertFalse(message.rich_payload)

    def test_plain_reply_with_no_json_block_has_no_rich_payload(self):
        session = self._create_session()
        with self._mock_provider_call(text="just a plain answer"):
            session.action_send_message("hello")
        message = session.message_ids.filtered(lambda m: m.role == "assistant")
        self.assertFalse(message.rich_payload)
        self.assertFalse(message.tool_calls)

    def test_extract_rich_payload_ignores_a_json_block_without_components_key(self):
        session = self._create_session()
        payload, text = session._extract_rich_payload('Some text\n```json\n{"foo": "bar"}\n```')
        self.assertIsNone(payload)
        self.assertIn("```json", text)


class TestDeployfleetAICorePolicyGates(TestDeployfleetAICoreBase):
    def test_ai_disabled_globally_blocks_call(self):
        self.policy.ai_enabled = False
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

    def test_disabled_feature_blocks_call(self):
        self.feature.enabled = False
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

    def test_unknown_feature_blocks_call(self):
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("does_not_exist", "sys", "hello")

    def test_blocked_data_category_blocks_call(self):
        self.feature.data_category = "payroll"
        self.assertTrue(self.policy.block_payroll_data, "payroll should be blocked by default")
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

    def test_allowed_data_category_does_not_block(self):
        self.feature.data_category = "fleet_analytics"
        self.assertFalse(self.policy.block_fleet_analytics)
        with self._mock_provider_call():
            result = self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")
        self.assertEqual(result, "mocked response")

    def test_external_providers_disallowed_blocks_non_local_provider(self):
        self.policy.external_providers_allowed = False
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")


class TestDeployfleetAICoreBudget(TestDeployfleetAICoreBase):
    def test_cost_limit_already_exceeded_blocks_call(self):
        budget = self.env["deployfleet.ai.budget"].search([("company_id", "=", self.env.company.id)], limit=1)
        budget.monthly_cost_limit_usd = 0.0001
        self.env["deployfleet.ai.usage"].create({
            "company_id": self.env.company.id,
            "feature": "test_feature",
            "provider": "deepseek",
            "estimated_cost_usd": 5.0,
            "state": "success",
        })
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")


class TestDeployfleetAICoreCaching(TestDeployfleetAICoreBase):
    def test_second_identical_call_hits_cache_and_skips_provider(self):
        with self._mock_provider_call(text="first response") as mocked:
            result1 = self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")
            self.assertEqual(mocked.call_count, 1)

        # Provider is intentionally NOT mocked here — if the cache doesn't
        # short-circuit, this call would raise for lack of a real API key/network.
        result2 = self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")
        self.assertEqual(result1, result2)

        cache = self.env["deployfleet.ai.response.cache"].search([("feature", "=", "test_feature")])
        self.assertEqual(len(cache), 1)
        self.assertEqual(cache.hit_count, 1)

    def test_usage_logged_with_cache_hit_flag(self):
        with self._mock_provider_call():
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")
        self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

        logs = self.env["deployfleet.ai.usage"].search([("feature", "=", "test_feature")], order="call_date asc")
        self.assertEqual(len(logs), 2)
        self.assertFalse(logs[0].cache_hit)
        self.assertTrue(logs[1].cache_hit)
        self.assertEqual(logs[1].tokens_in, 0)


class TestDeployfleetAICoreUsageLogging(TestDeployfleetAICoreBase):
    def test_successful_call_logs_usage(self):
        with self._mock_provider_call(tokens_in=100, tokens_out=50):
            self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

        log = self.env["deployfleet.ai.usage"].search([("feature", "=", "test_feature")], limit=1)
        self.assertEqual(log.state, "success")
        self.assertEqual(log.tokens_in, 100)
        self.assertEqual(log.tokens_out, 50)
        self.assertGreater(log.estimated_cost_usd, 0.0)

    def test_failed_call_logs_error_and_reraises(self):
        with patch.object(type(self.env["deployfleet.ai.core"]), "_call_provider", side_effect=ValueError("boom")):
            with self.assertRaises(ValueError):
                self.env["deployfleet.ai.core"].complete("test_feature", "sys", "hello")

        log = self.env["deployfleet.ai.usage"].search([("feature", "=", "test_feature")], limit=1)
        self.assertEqual(log.state, "error")
        self.assertIn("boom", log.error_message)


class TestDeployfleetAICoreHelpers(TestDeployfleetAICoreBase):
    def test_cache_key_is_deterministic_and_feature_scoped(self):
        core = self.env["deployfleet.ai.core"]
        key1 = core._make_cache_key("feature_a", "sys", "hello")
        key2 = core._make_cache_key("feature_a", "sys", "hello")
        key3 = core._make_cache_key("feature_b", "sys", "hello")
        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_model_for_tier_returns_configured_model(self):
        self.assertEqual(self.config._model_for_tier("deepseek", "cheap"), "deepseek-chat")
        self.assertEqual(self.config._model_for_tier("deepseek", "reasoning"), "deepseek-reasoner")

    def test_estimate_cost_zero_for_unknown_provider(self):
        core = self.env["deployfleet.ai.core"]
        self.assertEqual(core._estimate_cost("unknown_provider", 1000, 1000), 0.0)


class TestDeployfleetAICoreProviderAdapters(TestDeployfleetAICoreBase):
    def test_openai_compatible_adapter_parses_response(self):
        core = self.env["deployfleet.ai.core"]
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "choices": [{"message": {"content": "hi there"}}],
            "usage": {"prompt_tokens": 12, "completion_tokens": 34},
        }
        with patch("odoo.addons.deployfleet_ai_core.models.deployfleet_ai_engine.requests") as mock_requests:
            mock_requests.post.return_value = fake_response
            text, tokens_in, tokens_out = core._call_openai_compatible(
                "deepseek", "fake-key", "deepseek-chat", "sys", "hello", 4096, 0.2
            )
        self.assertEqual(text, "hi there")
        self.assertEqual((tokens_in, tokens_out), (12, 34))

    def test_claude_adapter_parses_response(self):
        core = self.env["deployfleet.ai.core"]
        fake_response = MagicMock()
        fake_response.raise_for_status.return_value = None
        fake_response.json.return_value = {
            "content": [{"type": "text", "text": "hi from claude"}],
            "usage": {"input_tokens": 5, "output_tokens": 7},
        }
        with patch("odoo.addons.deployfleet_ai_core.models.deployfleet_ai_engine.requests") as mock_requests:
            mock_requests.post.return_value = fake_response
            text, tokens_in, tokens_out = core._call_claude(
                "fake-key", "claude-haiku-4-5-20251001", "sys", "hello", 4096, 0.2
            )
        self.assertEqual(text, "hi from claude")
        self.assertEqual((tokens_in, tokens_out), (5, 7))

    def test_gemini_adapter_raises_not_implemented(self):
        core = self.env["deployfleet.ai.core"]
        with self.assertRaises(NotImplementedError):
            core._call_provider("gemini", "key", "gemini-2.5-flash", "sys", "hello", 4096, 0.2)

    def test_local_adapter_raises_not_implemented(self):
        core = self.env["deployfleet.ai.core"]
        with self.assertRaises(NotImplementedError):
            core._call_provider("local", None, "local-model", "sys", "hello", 4096, 0.2)


class TestDeployfleetAICoreToolCalling(TestDeployfleetAICoreBase):
    """Regression tests for complete_with_tools() and its two
    provider-native tool-calling adapters (docs/architecture/
    21-copilot-rail-architecture.md §3/§10 Phase 1b)."""

    def _mock_tool_call(self, text="tool-informed answer", tokens_in=5, tokens_out=5):
        return patch.object(
            type(self.env["deployfleet.ai.core"]),
            "_call_provider_with_tools",
            return_value=(text, tokens_in, tokens_out),
        )

    def test_complete_with_tools_returns_provider_text_and_logs_usage(self):
        tools = [{"name": "noop", "description": "does nothing", "parameters": {"type": "object", "properties": {}}}]
        with self._mock_tool_call(text="42 vehicles active"):
            result = self.env["deployfleet.ai.core"].complete_with_tools(
                "test_feature", "sys", "how many vehicles?", tools,
            )
        self.assertEqual(result, "42 vehicles active")
        log = self.env["deployfleet.ai.usage"].search([("feature", "=", "test_feature")], limit=1)
        self.assertEqual(log.state, "success")
        self.assertFalse(log.cache_hit)

    def test_complete_with_tools_never_reads_or_writes_cache(self):
        tools = [{"name": "noop", "description": "x", "parameters": {}}]
        with self._mock_tool_call(text="first"):
            self.env["deployfleet.ai.core"].complete_with_tools("test_feature", "sys", "hello", tools)
        cache = self.env["deployfleet.ai.response.cache"].search([("feature", "=", "test_feature")])
        self.assertFalse(cache, "tool-calling responses must never populate the plain-text response cache")

    def test_complete_with_tools_respects_disabled_feature_gate(self):
        self.feature.enabled = False
        with self.assertRaises(UserError):
            self.env["deployfleet.ai.core"].complete_with_tools("test_feature", "sys", "hello", [])

    def test_openai_adapter_executes_tool_call_then_returns_final_text(self):
        core = self.env["deployfleet.ai.core"]
        tool_call_response = MagicMock()
        tool_call_response.raise_for_status.return_value = None
        tool_call_response.json.return_value = {
            "choices": [{"message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "call_1", "function": {"name": "get_thing", "arguments": '{"id": 7}'}}],
            }}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        final_response = MagicMock()
        final_response.raise_for_status.return_value = None
        final_response.json.return_value = {
            "choices": [{"message": {"role": "assistant", "content": "Thing 7 is fine."}}],
            "usage": {"prompt_tokens": 20, "completion_tokens": 8},
        }
        executor = MagicMock(return_value={"status": "fine"})
        tools = [{
            "name": "get_thing", "description": "gets a thing",
            "parameters": {"type": "object", "properties": {}},
        }]
        tool_call_log = []
        with patch("odoo.addons.deployfleet_ai_core.models.deployfleet_ai_engine.requests") as mock_requests:
            mock_requests.post.side_effect = [tool_call_response, final_response]
            text, tokens_in, tokens_out = core._call_openai_compatible_with_tools(
                "deepseek", "fake-key", "deepseek-chat", "sys", "hello", 4096, 0.2, tools, executor, tool_call_log,
            )
        self.assertEqual(text, "Thing 7 is fine.")
        self.assertEqual((tokens_in, tokens_out), (30, 13))
        executor.assert_called_once_with("get_thing", {"id": 7})
        self.assertEqual(tool_call_log, [{"tool": "get_thing", "args": {"id": 7}}])

    def test_claude_adapter_executes_tool_use_then_returns_final_text(self):
        core = self.env["deployfleet.ai.core"]
        tool_use_response = MagicMock()
        tool_use_response.raise_for_status.return_value = None
        tool_use_response.json.return_value = {
            "content": [{"type": "tool_use", "id": "toolu_1", "name": "get_thing", "input": {"id": 7}}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        final_response = MagicMock()
        final_response.raise_for_status.return_value = None
        final_response.json.return_value = {
            "content": [{"type": "text", "text": "Thing 7 is fine."}],
            "usage": {"input_tokens": 20, "output_tokens": 8},
        }
        executor = MagicMock(return_value={"status": "fine"})
        tools = [{
            "name": "get_thing", "description": "gets a thing",
            "parameters": {"type": "object", "properties": {}},
        }]
        tool_call_log = []
        with patch("odoo.addons.deployfleet_ai_core.models.deployfleet_ai_engine.requests") as mock_requests:
            mock_requests.post.side_effect = [tool_use_response, final_response]
            text, tokens_in, tokens_out = core._call_claude_with_tools(
                "fake-key", "claude-haiku-4-5-20251001", "sys", "hello", 4096, 0.2, tools, executor, tool_call_log,
            )
        self.assertEqual(text, "Thing 7 is fine.")
        self.assertEqual((tokens_in, tokens_out), (30, 13))
        executor.assert_called_once_with("get_thing", {"id": 7})
        self.assertEqual(tool_call_log, [{"tool": "get_thing", "args": {"id": 7}}])

    def test_tool_rounds_exhausted_degrades_gracefully_instead_of_looping(self):
        core = self.env["deployfleet.ai.core"]
        always_tool_call_response = MagicMock()
        always_tool_call_response.raise_for_status.return_value = None
        always_tool_call_response.json.return_value = {
            "choices": [{"message": {
                "role": "assistant", "content": None,
                "tool_calls": [{"id": "call_1", "function": {"name": "get_thing", "arguments": "{}"}}],
            }}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1},
        }
        executor = MagicMock(return_value={"ok": True})
        tools = [{"name": "get_thing", "description": "x", "parameters": {}}]
        with patch("odoo.addons.deployfleet_ai_core.models.deployfleet_ai_engine.requests") as mock_requests:
            mock_requests.post.return_value = always_tool_call_response
            text, _tokens_in, _tokens_out = core._call_openai_compatible_with_tools(
                "deepseek", "fake-key", "deepseek-chat", "sys", "hello", 4096, 0.2, tools, executor,
            )
        self.assertIn("wasn't able to finish", text)

    def test_execute_tool_call_returns_error_when_no_executor(self):
        core = self.env["deployfleet.ai.core"]
        result = core._execute_tool_call("anything", {}, None)
        self.assertIn("error", result)

    def test_execute_tool_call_catches_executor_exception(self):
        core = self.env["deployfleet.ai.core"]

        def boom(_name, _args):
            raise ValueError("kaboom")

        result = core._execute_tool_call("anything", {}, boom)
        self.assertIn("kaboom", result)
