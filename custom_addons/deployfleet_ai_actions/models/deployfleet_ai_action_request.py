import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Categorically off-limits for an AI-proposed write, regardless of who
# approves it - auth/security/system configuration is a different class
# of risk than a maintenance record or a dispatch note, and closing this
# off at submission time (not just trusting the approver's judgment) is
# cheap insurance for what CLAUDE.md flags as hard risk #7.
_FORBIDDEN_TARGET_MODELS = {
    "res.users", "res.groups", "res.groups.privilege", "ir.rule", "ir.model.access",
    "ir.config_parameter", "ir.model", "ir.model.fields", "ir.actions.server",
    "deployfleet.ai.action.request", "deployfleet.ai.permission", "deployfleet.ai.policy",
}


class DeployfleetAIActionRequest(models.Model):
    """The mandatory suggestion -> permission check -> human approval ->
    execute -> audit pipeline for any AI-initiated write - see
    docs/architecture/08-ai-architecture.md §5, a hard constraint, not a
    design preference, and CLAUDE.md §4 / hard risk #7: "there is no
    auto-execute path in v1". Enforced structurally, not just by
    convention: `_execute()` is a private method with exactly one caller
    anywhere in this module, `action_approve()`, which itself refuses to
    run unless `state == 'pending_approval'` and the approving user holds
    a role explicitly trusted to approve writes. No cron, no server
    action, and no other code path in this module reaches `_execute()`.
    """

    _name = "deployfleet.ai.action.request"
    _description = "DeployFleet AI Action Request"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    feature_id = fields.Many2one(
        "deployfleet.ai.feature", required=True,
        help="Which AI feature/agent proposed this action.",
    )
    action_type = fields.Char(required=True, help="e.g. 'create_maintenance_schedule'.")
    target_model = fields.Char(required=True, help="Technical model name the action writes to.")
    target_id = fields.Integer(help="Existing record to write to. Empty/0 means this action creates a record.")
    proposed_vals = fields.Text(
        required=True,
        help="JSON-encoded field values the action would write or create - exactly what "
             "the human approver sees before approving, not a summary of it.",
    )
    source_context = fields.Char(
        help="What triggered this request, e.g. 'whatsapp_message', 'dashboard_click', "
             "'scheduled_agent_run'.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("pending_approval", "Pending Approval"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("executed", "Executed"),
            ("failed", "Failed"),
        ],
        default="draft",
        required=True,
    )
    requested_by = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    approved_by = fields.Many2one("res.users", readonly=True, copy=False)
    executed_at = fields.Datetime(readonly=True, copy=False)
    rejection_reason = fields.Char()
    error_message = fields.Text(readonly=True, copy=False)
    result_record_id = fields.Integer(
        readonly=True, copy=False, help="ID of the record the executed action wrote to."
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.ai.action.request")
        return super().create(vals_list)

    @api.constrains("target_model")
    def _check_target_model_not_forbidden(self):
        for request in self:
            if request.target_model in _FORBIDDEN_TARGET_MODELS:
                raise UserError(
                    self.env._(
                        "AI-proposed actions may not target '%(model)s' - this model is "
                        "categorically off-limits regardless of who would approve it.",
                        model=request.target_model,
                    )
                )

    def action_submit_for_approval(self):
        for request in self:
            if request.state != "draft":
                raise UserError(self.env._("Only a draft request can be submitted for approval."))
            request.state = "pending_approval"

    def action_reject(self, reason=None):
        """Deliberately re-checks the rejecter's own authority in Python,
        the same defense-in-depth reasoning as action_approve() below -
        a view restriction (or an ACL row) is a UI convenience, not a
        security boundary a method should silently rely on alone."""
        approver_group = "deployfleet_security.group_deployfleet_manager"
        if not self.env.user.has_group(approver_group):
            raise UserError(self.env._("Only a fleet manager or above may reject AI-proposed actions."))
        for request in self:
            if request.state != "pending_approval":
                raise UserError(self.env._("Only a pending request can be rejected."))
            request.write({"state": "rejected", "rejection_reason": reason})

    def action_approve(self):
        """The one and only gate an AI-proposed write can pass through.
        Deliberately re-checks the approver's own authority here rather
        than trusting a view-level button restriction alone - a view
        restriction is a UI convenience, not a security boundary."""
        approver_group = "deployfleet_security.group_deployfleet_manager"
        if not self.env.user.has_group(approver_group):
            raise UserError(self.env._("Only a fleet manager or above may approve AI-proposed actions."))
        for request in self:
            if request.state != "pending_approval":
                raise UserError(self.env._("Only a pending request can be approved."))
            request.write({"state": "approved", "approved_by": self.env.user.id})
            request._execute()

    def _execute(self):
        """Writes via the normal ORM, as the *approver*, never sudo() - an
        AI-proposed action is subject to exactly the same access rights
        and field validation a human entering the same data by hand would
        be. Never call this directly; it is only ever invoked from
        action_approve(), immediately after that method's own state and
        permission checks pass."""
        self.ensure_one()
        if self.state != "approved":
            raise UserError(self.env._("An action can only execute immediately after approval."))
        try:
            vals = json.loads(self.proposed_vals)
        except (TypeError, ValueError) as exc:
            self.write({"state": "failed", "error_message": f"Invalid proposed_vals JSON: {exc}"})
            return

        try:
            model = self.env[self.target_model]
            if self.target_id:
                record = model.browse(self.target_id)
                record.write(vals)
                result_id = record.id
            else:
                record = model.create(vals)
                result_id = record.id
        except Exception as exc:  # noqa: BLE001 — a failed write must be recorded, never raised past this point
            _logger.error("deployfleet_ai_actions: execution failed for request %s: %s", self.name, exc)
            self.write({"state": "failed", "error_message": str(exc)})
            return

        self.write({
            "state": "executed", "executed_at": fields.Datetime.now(), "result_record_id": result_id,
        })
