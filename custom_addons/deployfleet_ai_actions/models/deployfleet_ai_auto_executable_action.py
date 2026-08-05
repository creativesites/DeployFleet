from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetAIAutoExecutableAction(models.Model):
    """Allow-list of {action_type, target_model, action_method} triples an
    AI-proposed action_method call may ever execute through this pipeline
    - docs/architecture/21-copilot-rail-architecture.md §4's auto-executable
    tier, broadened by an engineering-audit fix (see `auto_execute` below).
    A narrow, deliberate, reviewed exception to CLAUDE.md §4 / hard risk #7's
    "no auto-execute path in v1" rule, not a reversal of it: only entries in
    this table, matched exactly on all three fields, are ever eligible -
    deployfleet.ai.action.request.propose() checks this table (plus its own
    data-category re-check) before ever bypassing the approval queue, and
    every other write still lands in pending_approval exactly as before
    this model existed.

    Engineering-audit fix: this table originally gated only the auto-exec
    *skip-approval* decision - a manually-approved action_method request
    was checked against nothing but the small, business-model-free
    _FORBIDDEN_TARGET_MODELS deny-list, so any producer calling propose()
    could set action_method to any action_*-prefixed method on any
    non-forbidden model (e.g. deployfleet.invoice.action_confirm, with its
    own accounting/ZRA side effects) and it would reach pending_approval
    and execute exactly as approved - undermining the premise that a
    manager's approval is an informed one, especially since the approval
    screens didn't even render action_method (a separate half of the same
    finding, fixed in deployfleet_ui). `_execute()` now requires an
    allow-list match for every action_method call, manual or auto; the new
    `auto_execute` field is a strictly narrower flag *within* that broader
    set - "may this pipeline ever call this method at all" vs. "may it
    skip a human's approval for this method."

    action_method is required, matching this tier's own reasoning: the
    doc's concrete starting examples (action_set_available(),
    action_confirm()) are all zero-arg state-transition methods, not
    plain field writes - a bare create/write auto-exec entry would need a
    much stronger reversibility argument than this tier is meant to
    carry.
    """

    _name = "deployfleet.ai.auto.executable.action"
    _description = "DeployFleet AI Executable-Action Allow-List"
    _order = "action_type"

    action_type = fields.Char(required=True, help="Matches deployfleet.ai.action.request.action_type.")
    target_model = fields.Char(required=True)
    action_method = fields.Char(
        required=True,
        help="The zero-arg action_*() method this allow-list entry permits calling through "
             "the AI action pipeline - manually approved, or automatically if auto_execute "
             "is also set.",
    )
    auto_execute = fields.Boolean(
        default=True,
        help="If set, a matching request also skips human approval entirely (the original "
             "doc 21 §4 tier). If unset, the method may still be manually approved and "
             "executed - it just always waits for a human, the same as any other action - "
             "but it's on this table so an admin has explicitly reviewed and permitted it, "
             "rather than any producer being able to name an arbitrary action_* method.",
    )
    description = fields.Text(
        help="Why this specific action is safe to permit through this pipeline - doc 21 §4's "
             "reversibility/cost criteria for an auto_execute entry, or simply why a human "
             "should be trusted to approve it for a non-auto_execute entry.",
    )

    _sql_constraints = [
        (
            "action_type_unique", "UNIQUE(action_type)",
            "Each auto-executable action_type may only be allow-listed once.",
        ),
    ]

    @api.constrains("action_method")
    def _check_action_method_prefix(self):
        for entry in self:
            if not entry.action_method.startswith("action_"):
                raise UserError(self.env._(
                    "Auto-executable action_method '%(method)s' must start with 'action_', "
                    "matching this codebase's own state-transition method convention.",
                    method=entry.action_method,
                ))
