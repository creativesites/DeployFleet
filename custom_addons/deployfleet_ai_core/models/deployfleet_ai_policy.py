from odoo import fields, models


class DeployfleetAIPolicy(models.Model):
    """Per-company AI governance policy — the resolved shape from
    docs/architecture/06-risks-and-recommendations.md risk #8:

        AI Enabled: Yes
        External AI Providers: Allowed
        Payroll Data: Blocked
        Financial Data: Blocked
        Fleet Analytics: Allowed

    Every call into `deployfleet.ai.core.complete()` checks this policy
    first — a blocked data category never reaches the provider router,
    regardless of cache state. Per-role scoping (which *user* can ask
    which agent) is a separate, later concern owned by
    `deployfleet_ai_permissions` (Phase 4) — this model is the
    company-wide gate, not the user-level one.
    """

    _name = "deployfleet.ai.policy"
    _description = "DeployFleet Company AI Policy"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    ai_enabled = fields.Boolean(default=True, string="AI Enabled")
    external_providers_allowed = fields.Boolean(
        default=True,
        string="External AI Providers Allowed",
        help="If disabled, only the reserved 'local' provider slot may be used — "
             "external calls (DeepSeek/OpenAI/Claude/Gemini) are refused outright.",
    )
    block_payroll_data = fields.Boolean(
        default=True,
        help="Safe-by-default: payroll/salary-adjacent AI features are blocked until explicitly allowed.",
    )
    block_financial_data = fields.Boolean(
        default=True,
        help="Safe-by-default: billing/financial AI features are blocked until explicitly allowed.",
    )
    block_fleet_analytics = fields.Boolean(
        default=False,
        help="Fleet/dispatch/maintenance analytics are allowed by default — "
             "lower sensitivity than payroll or financial data.",
    )

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Only one AI policy per company."),
    ]

    def _is_category_blocked(self, data_category):
        self.ensure_one()
        return {
            "payroll": self.block_payroll_data,
            "financial": self.block_financial_data,
            "fleet_analytics": self.block_fleet_analytics,
        }.get(data_category, False)
