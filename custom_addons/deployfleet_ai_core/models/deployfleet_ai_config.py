from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetAIConfig(models.Model):
    """Provider credentials, model selection, and cache/budget parameters —
    the technical counterpart to `deployfleet.ai.policy`'s governance
    concerns. One active record per company.
    """

    _name = "deployfleet.ai.config"
    _description = "DeployFleet AI Provider Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    active_provider = fields.Selection(
        [
            ("deepseek", "DeepSeek"),
            ("openai", "OpenAI"),
            ("claude", "Claude (Anthropic)"),
            ("gemini", "Google Gemini"),
            ("local", "Local / self-hosted (reserved, not yet implemented)"),
        ],
        default="deepseek",
        required=True,
    )
    fallback_provider = fields.Selection(
        [
            ("none", "Disabled"),
            ("deepseek", "DeepSeek"),
            ("openai", "OpenAI"),
            ("claude", "Claude (Anthropic)"),
            ("gemini", "Google Gemini"),
        ],
        default="none",
    )

    deepseek_api_key = fields.Char(string="DeepSeek API Key", copy=False)
    deepseek_model_cheap = fields.Char(default="deepseek-chat")
    deepseek_model_reasoning = fields.Char(default="deepseek-reasoner")

    openai_api_key = fields.Char(string="OpenAI API Key", copy=False)
    openai_model_cheap = fields.Char(default="gpt-4o-mini")
    openai_model_reasoning = fields.Char(default="gpt-4o")

    claude_api_key = fields.Char(string="Claude API Key", copy=False)
    claude_model_cheap = fields.Char(default="claude-haiku-4-5-20251001")
    claude_model_reasoning = fields.Char(default="claude-opus-5")

    gemini_api_key = fields.Char(string="Gemini API Key", copy=False)
    gemini_model_cheap = fields.Char(default="gemini-2.5-flash")
    gemini_model_reasoning = fields.Char(default="gemini-2.5-pro")

    max_tokens = fields.Integer(default=4096)
    temperature = fields.Float(default=0.2)

    enable_response_cache = fields.Boolean(default=True)
    response_cache_ttl_hours = fields.Integer(default=24)
    enable_context_cache = fields.Boolean(default=True)
    context_cache_ttl_hours = fields.Integer(
        default=168, help="Long-lived cache for slow-changing entity context (default 7 days)."
    )

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Only one AI configuration per company."),
    ]

    @api.constrains("temperature")
    def _check_temperature(self):
        for config in self:
            if config.temperature < 0.0 or config.temperature > 1.0:
                raise ValidationError(self.env._("Temperature must be between 0.0 and 1.0."))

    @api.constrains("max_tokens")
    def _check_max_tokens(self):
        for config in self:
            if config.max_tokens < 100 or config.max_tokens > 8000:
                raise ValidationError(self.env._("Max tokens must be between 100 and 8000."))

    def _model_for_tier(self, provider, tier):
        """tier is 'cheap' or 'reasoning'."""
        self.ensure_one()
        field_name = f"{provider}_model_{tier}"
        if not hasattr(self, field_name):
            raise ValueError(f"Unknown provider/tier combination: {provider}/{tier}")
        return getattr(self, field_name)

    def _api_key_for_provider(self, provider):
        self.ensure_one()
        field_name = f"{provider}_api_key"
        return getattr(self, field_name, None)

    @api.model
    def get_active_config(self, company=None):
        company = company or self.env.company
        config = self.search([("company_id", "=", company.id)], limit=1)
        if not config:
            raise ValueError(
                f"No deployfleet.ai.config record for company {company.display_name}. "
                "One is created automatically on module install — check data/deployfleet_ai_config_data.xml."
            )
        return config
