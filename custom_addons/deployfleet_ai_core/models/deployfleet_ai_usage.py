from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetAIUsage(models.Model):
    """Per-call audit/cost log — kept close to the source's `security.ai.log`
    (docs/architecture/02-reuse-strategy.md §0), extended with `company_id`
    for multi-company cost attribution, which the source lacked.
    """

    _name = "deployfleet.ai.usage"
    _description = "DeployFleet AI Usage Log"
    _order = "call_date desc, id desc"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, index=True)
    feature = fields.Char(required=True, index=True)
    agent = fields.Char(help="Which of the (future) AI agent personas made this call, if any.")
    provider = fields.Char(required=True)
    model_name = fields.Char()
    call_date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    request_preview = fields.Text()
    response_preview = fields.Text()
    duration_ms = fields.Integer(default=0)
    tokens_in = fields.Integer(default=0)
    tokens_out = fields.Integer(default=0)
    estimated_cost_usd = fields.Float(digits=(10, 6), default=0.0)
    cache_hit = fields.Boolean(default=False)
    state = fields.Selection([("success", "Success"), ("error", "Error")], required=True, default="success")
    error_message = fields.Text()

    @api.model
    def total_cost_this_month(self, company=None):
        company = company or self.env.company
        month_start = fields.Date.today().replace(day=1)
        logs = self.search([
            ("company_id", "=", company.id),
            ("call_date", ">=", month_start),
            ("state", "=", "success"),
        ])
        return sum(logs.mapped("estimated_cost_usd")), sum(logs.mapped("tokens_in")) + sum(logs.mapped("tokens_out"))


class DeployfleetAIBudget(models.Model):
    """Pre-call budget gate — the source's usage tracking was entirely
    retrospective (compute stats from logs, no pre-call check). This is new:
    `deployfleet.ai.core.complete()` calls `_check_budget()` before making a
    provider call, not just after.
    """

    _name = "deployfleet.ai.budget"
    _description = "DeployFleet AI Monthly Budget"
    _rec_name = "company_id"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    monthly_token_limit = fields.Integer(default=0, help="0 = unlimited.")
    monthly_cost_limit_usd = fields.Float(default=0.0, help="0 = unlimited.")
    alert_threshold_pct = fields.Integer(
        default=80, help="Log a warning once usage crosses this percentage of either limit."
    )

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Only one AI budget per company."),
    ]

    def _check_budget(self):
        """Raises UserError if either limit is already exceeded. Does not
        block on the alert threshold — that's a warning, not a hard stop."""
        self.ensure_one()
        usage_model = self.env["deployfleet.ai.usage"]
        cost_used, tokens_used = usage_model.total_cost_this_month(self.company_id)

        if self.monthly_cost_limit_usd and cost_used >= self.monthly_cost_limit_usd:
            raise UserError(self.env._(
                "DeployFleet AI monthly cost limit reached for %(company)s ($%(used).2f of $%(limit).2f).",
                company=self.company_id.display_name, used=cost_used, limit=self.monthly_cost_limit_usd,
            ))
        if self.monthly_token_limit and tokens_used >= self.monthly_token_limit:
            raise UserError(self.env._(
                "DeployFleet AI monthly token limit reached for %(company)s (%(used)s of %(limit)s).",
                company=self.company_id.display_name, used=tokens_used, limit=self.monthly_token_limit,
            ))
        return cost_used, tokens_used
