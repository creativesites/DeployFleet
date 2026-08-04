import hashlib
import json
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

# One round to let the provider call tools, one forced-final round with
# tools withheld so a misbehaving provider can't loop indefinitely —
# see docs/architecture/21-copilot-rail-architecture.md §3.
_MAX_TOOL_ROUNDS = 2


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

        # sudo() from here down: deployfleet.ai.config holds provider API
        # keys and is deliberately locked to base.group_system-only ACLs
        # (nobody should be able to browse another user's credentials by
        # opening the model directly) — but that same lockdown was also
        # silently blocking every real operational role from using AI at
        # all, since complete() itself couldn't read its own config,
        # budget, or cache. The policy/feature/permission checks above
        # this point (and the AI-permissions check that runs before
        # complete() is even entered — see deployfleet_ai_permissions)
        # are the actual access boundary; everything below is this
        # router's own trusted internal bookkeeping, not something a
        # caller should need direct model access to.
        config = self.env["deployfleet.ai.config"].sudo().get_active_config(company)
        provider = feature.provider_override or config.active_provider

        if provider != "local" and not policy.external_providers_allowed:
            raise UserError(self.env._(
                "External AI providers are disabled for %(company)s; "
                "feature '%(feature)s' requested provider '%(provider)s'.",
                company=company.display_name, feature=feature_key, provider=provider,
            ))

        budget = self.env["deployfleet.ai.budget"].sudo().search([("company_id", "=", company.id)], limit=1)
        if budget:
            budget._check_budget()

        cache_key = self._make_cache_key(feature_key, system_prompt, user_message)
        if config.enable_response_cache:
            cached = self.env["deployfleet.ai.response.cache"].sudo().search([("cache_key", "=", cache_key)], limit=1)
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
            self.env["deployfleet.ai.response.cache"].sudo().create({
                "cache_key": cache_key, "feature": feature_key, "response": response_text,
            })

        self._log_usage(
            company, feature, provider, model_name, tokens_in, tokens_out, cost, duration_ms,
            cache_hit=False, state="success",
            request_preview=user_message[:500], response_preview=response_text[:500],
        )
        return response_text

    @api.model
    # Mirrors complete()'s own parameter list plus the tool-calling-specific
    # additions - a dict-based signature would just move the same complexity
    # into every call site instead of removing it.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def complete_with_tools(
        self, feature_key, system_prompt, user_message, tools, executor=None, company=None, tool_call_log=None,
    ):
        """Like complete(), but lets the provider call back into a bounded
        set of tools (function/tool-calling) before producing its final
        answer. Tool results are live data, so — unlike complete() — this
        path never reads or writes the response cache.

        `tools` is a list of {"name", "description", "parameters"} dicts
        (JSON Schema `parameters`, no provider-specific wrapper — the
        adapters below reshape per provider). `executor(name, arguments)`
        is called for each tool the provider selects and must return a
        JSON-serializable result; passing no executor is safe (tool calls
        just come back as an error string the model can react to).

        `tool_call_log`, if a list is passed, gets one {"tool", "args"}
        dict appended per tool call actually executed (doc 21 §5's
        transparency field on deployfleet.ai.chat.message) - a side
        channel rather than a return-value change, so complete_with_tools()'s
        existing (text, tokens_in, tokens_out)-shaped internals don't need
        to change shape for callers that don't care."""
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

        # sudo() from here down — same trusted-router reasoning as complete() above.
        config = self.env["deployfleet.ai.config"].sudo().get_active_config(company)
        provider = feature.provider_override or config.active_provider

        if provider != "local" and not policy.external_providers_allowed:
            raise UserError(self.env._(
                "External AI providers are disabled for %(company)s; "
                "feature '%(feature)s' requested provider '%(provider)s'.",
                company=company.display_name, feature=feature_key, provider=provider,
            ))

        budget = self.env["deployfleet.ai.budget"].sudo().search([("company_id", "=", company.id)], limit=1)
        if budget:
            budget._check_budget()

        model_name = config._model_for_tier(provider, feature.model_tier)
        api_key = config._api_key_for_provider(provider)

        start = time.monotonic()
        try:
            response_text, tokens_in, tokens_out = self._call_provider_with_tools(
                provider, api_key, model_name, system_prompt, user_message,
                config.max_tokens, config.temperature, tools, executor, tool_call_log,
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
        # sudo(): the usage log is an audit trail the router itself
        # populates, not something a caller should need direct create
        # access to (base.group_user is deliberately read-only on this
        # model so the Copilot Console's dashboard can still list it).
        self.env["deployfleet.ai.usage"].sudo().create({
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
    # Mirrors _call_provider()'s own parameter list plus tools/executor/
    # tool_call_log — a dict-based signature would just move the same
    # complexity into every call site instead of removing it.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def _call_provider_with_tools(self, provider, api_key, model_name, system_prompt, user_message,
                                   max_tokens, temperature, tools, executor, tool_call_log=None):
        if provider in ("deepseek", "openai"):
            return self._call_openai_compatible_with_tools(
                provider, api_key, model_name, system_prompt, user_message,
                max_tokens, temperature, tools, executor, tool_call_log,
            )
        if provider == "claude":
            return self._call_claude_with_tools(
                api_key, model_name, system_prompt, user_message,
                max_tokens, temperature, tools, executor, tool_call_log,
            )
        raise NotImplementedError(
            f"Tool-calling is not implemented for provider '{provider}' "
            "(only deepseek/openai/claude support it in this router)."
        )

    @api.model
    def _execute_tool_call(self, name, arguments, executor, tool_call_log=None):
        """Runs one provider-selected tool call and returns a JSON string
        result suitable for feeding back to the provider. Never raises —
        an unknown tool, a bad argument, or an executor exception all
        become an error string the model can react to instead of aborting
        the whole exchange over what might be recoverable. Records the
        call in `tool_call_log` (if a list was passed) regardless of
        outcome — a failed tool call is still worth surfacing in doc 21
        §5's transparency detail."""
        if tool_call_log is not None:
            tool_call_log.append({"tool": name, "args": arguments})
        if not executor:
            return json.dumps({"error": "No tool executor is available in this context."})
        try:
            result = executor(name, arguments)
        except Exception as exc:  # noqa: BLE001 — feed failures back to the model, don't crash the chat turn
            return json.dumps({"error": str(exc)})
        return result if isinstance(result, str) else json.dumps(result)

    @api.model
    # A bounded tool-calling round loop naturally needs one local per piece of
    # accumulated state (messages, running token counts, per-round payload) —
    # splitting it up would scatter that state across artificial helper calls.
    # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    def _call_openai_compatible_with_tools(
        self, provider, api_key, model_name, system_prompt, user_message,
        max_tokens, temperature, tools, executor, tool_call_log=None,
    ):
        """OpenAI/DeepSeek function-calling: `tools`/`tool_choice` on the
        request, `message.tool_calls[].function.{name,arguments}` (a JSON
        *string*) on the response, answered with `role: "tool"` follow-up
        messages carrying `tool_call_id`."""
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

        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters") or {"type": "object", "properties": {}},
                },
            }
            for tool in tools
        ]

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        total_tokens_in = 0
        total_tokens_out = 0

        for round_index in range(_MAX_TOOL_ROUNDS):
            is_last_round = round_index == _MAX_TOOL_ROUNDS - 1
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if openai_tools and not is_last_round:
                payload["tools"] = openai_tools
                payload["tool_choice"] = "auto"

            response = requests.post(
                endpoint,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            total_tokens_in += usage.get("prompt_tokens", 0)
            total_tokens_out += usage.get("completion_tokens", 0)

            message = data["choices"][0]["message"]
            tool_calls = message.get("tool_calls")
            if not tool_calls:
                return message.get("content") or "", total_tokens_in, total_tokens_out

            messages.append(message)
            for call in tool_calls:
                fn = call.get("function", {})
                try:
                    arguments = json.loads(fn.get("arguments") or "{}")
                except ValueError:
                    result = json.dumps({"error": f"Invalid JSON arguments for tool '{fn.get('name')}'."})
                else:
                    result = self._execute_tool_call(fn.get("name"), arguments, executor, tool_call_log)
                messages.append({"role": "tool", "tool_call_id": call.get("id"), "content": result})

        return self._tool_rounds_exhausted_message(), total_tokens_in, total_tokens_out

    @api.model
    # Same reasoning as _call_openai_compatible_with_tools's own disable comment above.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def _call_claude_with_tools(
        self, api_key, model_name, system_prompt, user_message,
        max_tokens, temperature, tools, executor, tool_call_log=None,
    ):
        """Claude Messages API tool use: `tools` with `input_schema` on the
        request, `content` blocks of `type: "tool_use"` on the response,
        answered with a follow-up `user` message carrying `tool_result`
        content blocks keyed by `tool_use_id`."""
        if not requests:
            raise UserError(self.env._(
                "The 'requests' Python package is required for AI provider calls but is not installed."
            ))
        if not api_key:
            raise UserError(self.env._("No API key configured for provider 'claude'."))

        claude_tools = [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "input_schema": tool.get("parameters") or {"type": "object", "properties": {}},
            }
            for tool in tools
        ]

        messages = [{"role": "user", "content": user_message}]
        total_tokens_in = 0
        total_tokens_out = 0

        for round_index in range(_MAX_TOOL_ROUNDS):
            is_last_round = round_index == _MAX_TOOL_ROUNDS - 1
            payload = {
                "model": model_name,
                "system": system_prompt,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if claude_tools and not is_last_round:
                payload["tools"] = claude_tools

            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            usage = data.get("usage", {})
            total_tokens_in += usage.get("input_tokens", 0)
            total_tokens_out += usage.get("output_tokens", 0)

            content_blocks = data.get("content", [])
            tool_use_blocks = [block for block in content_blocks if block.get("type") == "tool_use"]
            if not tool_use_blocks:
                text = "".join(block.get("text", "") for block in content_blocks)
                return text, total_tokens_in, total_tokens_out

            messages.append({"role": "assistant", "content": content_blocks})
            tool_result_blocks = [
                {
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": self._execute_tool_call(
                        block.get("name"), block.get("input") or {}, executor, tool_call_log,
                    ),
                }
                for block in tool_use_blocks
            ]
            messages.append({"role": "user", "content": tool_result_blocks})

        return self._tool_rounds_exhausted_message(), total_tokens_in, total_tokens_out

    @api.model
    def _tool_rounds_exhausted_message(self):
        return self.env._(
            "I wasn't able to finish gathering the information needed to answer that — "
            "please try rephrasing or asking a narrower question."
        )

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
