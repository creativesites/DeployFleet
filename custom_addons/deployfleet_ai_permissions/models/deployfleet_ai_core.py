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
