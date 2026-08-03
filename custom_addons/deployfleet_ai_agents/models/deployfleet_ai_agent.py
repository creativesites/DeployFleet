from odoo import fields, models


class DeployfleetAIAgent(models.Model):
    """One of the six agent personas from
    docs/architecture/08-ai-architecture.md §6: a named bundle of (system
    prompt template, default model tier, data-access scope, related
    modules) - data, not a distinct code module. All six share the same
    provider router, cache, usage tracking, and permission engine in
    deployfleet_ai_core/deployfleet_ai_permissions; `feature_id` is what
    actually plugs an agent into that machinery (routing, policy/data-
    category checks, per-role permission gating via
    deployfleet.ai.permission) - this model is the human-facing catalog
    entry, `feature_id` is the enforcement point.
    """

    _name = "deployfleet.ai.agent"
    _description = "DeployFleet AI Agent Persona"
    _order = "sequence, id"

    key = fields.Char(required=True, index=True, help="Stable identifier, e.g. 'fleet_analyst'.")
    name = fields.Char(required=True)
    description = fields.Text()
    feature_id = fields.Many2one(
        "deployfleet.ai.feature", required=True,
        help="The deployfleet_ai_core feature this agent's queries route through - "
             "policy/permission/budget/cache checks all key off this.",
    )
    system_prompt_template = fields.Text(
        required=True,
        help="Base system prompt passed to deployfleet.ai.core.complete() for this agent.",
    )
    related_models = fields.Char(
        help="Informational: comma-separated technical model names this agent primarily reasons over.",
    )
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("key_unique", "UNIQUE(key)", "Agent key must be unique."),
    ]
