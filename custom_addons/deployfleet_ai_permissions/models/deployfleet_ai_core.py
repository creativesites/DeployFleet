from odoo import api, models


class DeployfleetAICore(models.AbstractModel):
    """Adds the per-role permission check ahead of every other check
    deployfleet_ai_core.complete() already performs (policy, feature
    toggle, data category, provider, budget, cache) - see
    docs/architecture/08-ai-architecture.md §9. Extending via _inherit
    rather than deployfleet_ai_core depending on this module keeps the
    dependency direction one-way: permissions are optional governance
    layered on top of the core router, not a hard requirement to use AI
    at all."""

    _inherit = "deployfleet.ai.core"

    @api.model
    def complete(self, feature_key, system_prompt, user_message, company=None):
        self.env["deployfleet.ai.permission"]._check_user_allowed(self.env.user, feature_key)
        return super().complete(feature_key, system_prompt, user_message, company=company)

    @api.model
    # Matches complete_with_tools()'s own parameter list in deployfleet_ai_core.
    # pylint: disable=too-many-arguments,too-many-positional-arguments
    def complete_with_tools(
        self, feature_key, system_prompt, user_message, tools, executor=None, company=None, tool_call_log=None,
    ):
        # Engineering-audit fix: this permission gate was wired onto
        # complete() only. Four of the six shipped agents have tools
        # registered, so every Chat-tab conversation with them routes
        # through complete_with_tools() instead (deployfleet_ai_agents'
        # DeployfleetAIChatSession._get_reply() override) — meaning a
        # role explicitly blocked from a feature via a
        # deployfleet.ai.permission row could still fully converse with
        # it, and trigger its tools, simply by using Chat instead of
        # the Copilot Console's Ask box. The same check now runs ahead
        # of both entry points.
        self.env["deployfleet.ai.permission"]._check_user_allowed(self.env.user, feature_key)
        return super().complete_with_tools(
            feature_key, system_prompt, user_message, tools,
            executor=executor, company=company, tool_call_log=tool_call_log,
        )
