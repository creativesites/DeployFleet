from odoo import fields, models


class DeployfleetAIFeature(models.Model):
    """Per-feature/agent AI toggle. Deliberately data-driven rather than a
    fixed boolean field per feature (the source's `security.ai.config` had
    one boolean column per feature, e.g. `feature_billing_auditor`) — the
    same lesson from the event bus (risk #4) applies here: a module that
    adds a new AI-powered feature registers one of these as a data record,
    it never requires editing this core module's model definition.

    `key` is the stable identifier feature code calls
    `deployfleet.ai.core.complete()` with, e.g. 'fuel_anomaly_detection',
    'dispatch_optimizer', 'payslip_explain'.
    """

    _name = "deployfleet.ai.feature"
    _description = "DeployFleet AI Feature / Agent Toggle"
    _order = "sequence, id"

    key = fields.Char(required=True, index=True, help="Stable feature identifier used in code.")
    name = fields.Char(required=True)
    description = fields.Text()
    enabled = fields.Boolean(default=True)
    model_tier = fields.Selection(
        [("cheap", "Cheap / routine"), ("reasoning", "Reasoning / complex")],
        default="cheap",
        required=True,
    )
    data_category = fields.Selection(
        [
            ("general", "General"),
            ("payroll", "Payroll"),
            ("financial", "Financial"),
            ("fleet_analytics", "Fleet Analytics"),
        ],
        default="general",
        required=True,
        help="Checked against deployfleet.ai.policy's per-category block flags before every call.",
    )
    provider_override = fields.Selection(
        [
            ("", "Use company default"),
            ("deepseek", "DeepSeek"),
            ("openai", "OpenAI"),
            ("claude", "Claude (Anthropic)"),
            ("gemini", "Google Gemini"),
        ],
        default="",
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("key_unique", "UNIQUE(key)", "Feature key must be unique."),
    ]
