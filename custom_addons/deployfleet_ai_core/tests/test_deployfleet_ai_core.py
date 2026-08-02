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
