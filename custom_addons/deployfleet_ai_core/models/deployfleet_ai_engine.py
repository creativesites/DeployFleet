import hashlib
import logging
import time

from odoo import api, models
from odoo.exceptions import UserError

try:
    import requests
except ImportError:  # pragma: no cover — declared in __manifest__.py external_dependencies
    requests = None

_logger = logging.getLogger(__name__)

# Rough, deliberately-approximate USD per 1K tokens, split input/output.
# Not billing-accurate — good enough for budget-tracking and cost estimates
# until real per-provider pricing is wired in as a follow-up.
_COST_PER_1K_TOKENS = {
    "deepseek": (0.00027, 0.0011),
    "openai": (0.00015, 0.0006),
    "claude": (0.001, 0.005),
    "gemini": (0.000075, 0.0003),
    "local": (0.0, 0.0),
}


class DeployfleetAICore(models.AbstractModel):
    """The single entry point every DeployFleet AI feature calls. No
    business module is allowed to import `requests` and talk to a provider
    directly — see docs/architecture/08-ai-architecture.md and CLAUDE.md §4.
    """

    _name = "deployfleet.ai.core"
    _description = "DeployFleet AI Provider Router"

    @api.model
    def complete(self, feature_key, system_prompt, user_message, company=None):
        """Runs a feature's AI request through policy/permission/budget
        checks, the response cache, and finally the provider router.
        Returns the response text, or raises UserError/an adapter exception."""
        company = company or self.env.company

        policy = self.env["deployfleet.ai.policy"].search([("company_id", "=", company.id)], limit=1)
        if not policy or not policy.ai_enabled:
            raise UserError(self.env._("AI is disabled for %s.", company.display_name))

        feature = self.env["deployfleet.ai.feature"].search([("key", "=", feature_key)], limit=1)
        if not feature or not feature.enabled:
            raise UserError(self.env._("AI feature '%s' is not enabled or not registered.", feature_key))

        if policy._is_category_blocked(feature.data_category):
            raise UserError(self.env._(
                "AI feature '%(feature)s' is blocked by company policy (data category: %(category)s).",
                feature=feature_key, category=feature.data_category,
            ))

        config = self.env["deployfleet.ai.config"].get_active_config(company)
        provider = feature.provider_override or config.active_provider

        if provider != "local" and not policy.external_providers_allowed:
            raise UserError(self.env._(
                "External AI providers are disabled for %(company)s; "
                "feature '%(feature)s' requested provider '%(provider)s'.",
                company=company.display_name, feature=feature_key, provider=provider,
            ))

        budget = self.env["deployfleet.ai.budget"].search([("company_id", "=", company.id)], limit=1)
        if budget:
            budget._check_budget()

        cache_key = self._make_cache_key(feature_key, system_prompt, user_message)
        if config.enable_response_cache:
            cached = self.env["deployfleet.ai.response.cache"].search([("cache_key", "=", cache_key)], limit=1)
            if cached:
                cached.hit_count += 1
                self._log_usage(
                    company, feature, provider, model_name=None, tokens_in=0, tokens_out=0,
                    cost=0.0, duration_ms=0, cache_hit=True, state="success",
                    request_preview=user_message[:500], response_preview=cached.response[:500],
                )
                return cached.response

        model_name = config._model_for_tier(provider, feature.model_tier)
        api_key = config._api_key_for_provider(provider)

        start = time.monotonic()
        try:
            response_text, tokens_in, tokens_out = self._call_provider(
                provider, api_key, model_name, system_prompt, user_message,
                config.max_tokens, config.temperature,
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log_usage(
                company, feature, provider, model_name, tokens_in=0, tokens_out=0,
                cost=0.0, duration_ms=duration_ms, cache_hit=False, state="error",
                request_preview=user_message[:500], error_message=str(exc),
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)
        cost = self._estimate_cost(provider, tokens_in, tokens_out)

        if config.enable_response_cache:
            self.env["deployfleet.ai.response.cache"].create({
                "cache_key": cache_key, "feature": feature_key, "response": response_text,
            })

        self._log_usage(
            company, feature, provider, model_name, tokens_in, tokens_out, cost, duration_ms,
            cache_hit=False, state="success",
            request_preview=user_message[:500], response_preview=response_text[:500],
        )
        return response_text

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @api.model
    def _make_cache_key(self, feature_key, system_prompt, user_message):
        raw = f"{feature_key}|{system_prompt}|{user_message}".encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @api.model
    def _estimate_cost(self, provider, tokens_in, tokens_out):
        rate_in, rate_out = _COST_PER_1K_TOKENS.get(provider, (0.0, 0.0))
        return (tokens_in / 1000.0) * rate_in + (tokens_out / 1000.0) * rate_out

    @api.model
    # A dedicated logging helper naturally collects one parameter per column
    # it writes — a dict-based signature would just move the same complexity
    # into every call site instead of removing it.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def _log_usage(self, company, feature, provider, model_name, tokens_in, tokens_out, cost,
                    duration_ms, cache_hit, state, request_preview=None, response_preview=None,
                    error_message=None):
        self.env["deployfleet.ai.usage"].create({
            "company_id": company.id,
            "feature": feature.key,
            "provider": provider,
            "model_name": model_name,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": cost,
            "duration_ms": duration_ms,
            "cache_hit": cache_hit,
            "state": state,
            "request_preview": request_preview,
            "response_preview": response_preview,
            "error_message": error_message,
        })

    @api.model
    def _call_provider(self, provider, api_key, model_name, system_prompt, user_message, max_tokens, temperature):
        if provider in ("deepseek", "openai"):
            return self._call_openai_compatible(
                provider, api_key, model_name, system_prompt, user_message, max_tokens, temperature
            )
        if provider == "claude":
            return self._call_claude(api_key, model_name, system_prompt, user_message, max_tokens, temperature)
        if provider == "gemini":
            raise NotImplementedError(
                "Gemini adapter is not yet implemented — reserved provider slot, tracked for a later phase."
            )
        if provider == "local":
            raise NotImplementedError(
                "Local/self-hosted model provider is a reserved slot, not yet implemented "
                "(see docs/architecture/08-ai-architecture.md §2)."
            )
        # Internal error, not user-facing — provider comes from a Selection field.
        raise ValueError(f"Unknown AI provider: {provider}")

    @api.model
    def _call_openai_compatible(
        self, provider, api_key, model_name, system_prompt, user_message, max_tokens, temperature
    ):
        """DeepSeek and OpenAI both expose an OpenAI-style chat completions
        endpoint — one HTTP call shape serves both."""
        if not requests:
            raise UserError(self.env._(
                "The 'requests' Python package is required for AI provider calls but is not installed."
            ))
        if not api_key:
            raise UserError(self.env._("No API key configured for provider '%s'.", provider))

        endpoint = {
            "deepseek": "https://api.deepseek.com/chat/completions",
            "openai": "https://api.openai.com/v1/chat/completions",
        }[provider]

        response = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    @api.model
    def _call_claude(self, api_key, model_name, system_prompt, user_message, max_tokens, temperature):
        if not requests:
            raise UserError(self.env._(
                "The 'requests' Python package is required for AI provider calls but is not installed."
            ))
        if not api_key:
            raise UserError(self.env._("No API key configured for provider 'claude'."))

        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model_name,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        return text, usage.get("input_tokens", 0), usage.get("output_tokens", 0)
