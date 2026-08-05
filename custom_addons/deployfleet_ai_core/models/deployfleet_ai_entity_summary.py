from odoo import api, fields, models


class DeployfleetAIEntitySummary(models.Model):
    """A small, deterministic-computed structured summary cache for one
    entity (e.g. a vehicle) - docs/architecture/
    21-copilot-rail-architecture.md §6's context/memory layer. Never a
    source of truth in its own right: the ORM record it summarizes
    always is. Deliberately NOT an LLM-generated summary - a second
    provider call per cache-miss would double the cost/latency of every
    tool call that uses it for no clear benefit over a plain Python
    string built from data the caller already read; `summary_text` is
    computed by whichever business module calls upsert(), using ordinary
    string formatting, not a second complete()/complete_with_tools() call.

    Invalidation is a hybrid, not pure event-bus pub/sub: `source_signature`
    lets a reader cheaply detect "nothing changed" on every read (the
    general-case mechanism, since not every field this cache might ever
    summarize publishes a bus event today) *and* one real event-bus
    subscription (_handle_bus_event() below, see data/
    deployfleet_ai_entity_summary_event_subscriptions.xml) proactively
    deletes a stale vehicle summary the moment a trip completes or a
    dispatch assigns a vehicle - the "invalidate on vehicle status
    changes, dispatch assigned, trip completed" behavior doc 21 §6
    describes, implemented with this codebase's existing event-bus
    infrastructure (deployfleet_event_bus) rather than a new pub/sub
    layer, and without deployfleet_ai_core ever depending on
    deployfleet_trip/deployfleet_dispatch - the subscription only needs
    an event-name string and this model's own name/method, both already
    resolvable without an import.
    """

    _name = "deployfleet.ai.entity.summary"
    _description = "DeployFleet AI Entity Summary Cache"
    _order = "computed_date desc"

    # Engineering-audit fix (C-01): no company_id/ir.rule existed on this
    # base.group_system-only model - a system admin belonging to one
    # company could still browse another company's cached vehicle
    # summaries table-wide. upsert() runs under sudo() (see
    # deployfleet_ai_agents' get_vehicle_summary tool), so this default
    # still resolves to the real calling user's own active company.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company, index=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    summary_text = fields.Text(required=True)
    computed_date = fields.Datetime(required=True, default=fields.Datetime.now)
    source_signature = fields.Char(
        required=True,
        help="Hash of the inputs used to compute summary_text - lets a caller cheaply detect "
             "'nothing changed' without recomputing the summary on every read.",
    )

    _sql_constraints = [
        ("res_model_res_id_unique", "UNIQUE(res_model, res_id)", "Only one cached summary per entity."),
    ]

    @api.model
    def get_cached(self, res_model, res_id):
        return self.search([("res_model", "=", res_model), ("res_id", "=", res_id)], limit=1)

    @api.model
    def upsert(self, res_model, res_id, summary_text, source_signature):
        existing = self.get_cached(res_model, res_id)
        vals = {
            "res_model": res_model, "res_id": res_id,
            "summary_text": summary_text, "source_signature": source_signature,
            "computed_date": fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
            return existing
        return self.create(vals)

    @api.model
    def _handle_bus_event(self, _event_name, _source_model, _source_id, payload):
        """Event bus subscriber - see data/
        deployfleet_ai_entity_summary_event_subscriptions.xml. Deletes
        (rather than recomputes) the cached vehicle summary named in the
        event payload's vehicle_id - the next tool call that wants it
        recomputes from live data on its own; this handler's only job is
        making sure that next read doesn't serve something stale.

        sudo(): this model is deliberately base.group_system-only (same
        lockdown as deployfleet.ai.response.cache), but the event bus
        dispatcher (deployfleet.event.log._dispatch_event()) invokes every
        subscriber's handler using the *publisher's* env, unchanged - a
        dispatcher confirming an assignment or completing a trip is
        neither of those things a real trucking-company user is, so
        without sudo() this handler would raise AccessError and, worse,
        the event bus swallows subscriber exceptions (never breaking the
        publisher), silently leaving stale cache entries behind forever."""
        vehicle_id = (payload or {}).get("vehicle_id")
        if not vehicle_id:
            return
        self.sudo().search([("res_model", "=", "deployfleet.vehicle"), ("res_id", "=", vehicle_id)]).unlink()


class DeployfleetAICompanyProfile(models.Model):
    """Company-scoped free-text context folded into Chat's system prompt
    (doc 21 §6) - fleet size, operating regions, business-rule notes an
    agent should already know without the user re-explaining it every
    conversation. A minimal stock admin form, not a custom deployfleet_ui
    screen - pure admin/system configuration a user never opens to do
    their job, the same exemption CLAUDE.md §5 / doc 20 §2 already carve
    out for AI provider config, notification rules, and the rest of this
    module's own admin-only screens.
    """

    _name = "deployfleet.ai.company.profile"
    _description = "DeployFleet AI Company Profile"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    profile_text = fields.Text(
        help="Free-text fleet size / operating-region / business-rule notes folded into every "
             "Chat session's system prompt for this company (doc 21 §6).",
    )
    updated_date = fields.Datetime(default=fields.Datetime.now)

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Each company may only have one AI company profile."),
    ]

    def write(self, vals):
        vals.setdefault("updated_date", fields.Datetime.now())
        return super().write(vals)
