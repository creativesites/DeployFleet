from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetAIAutoExecutableAction(models.Model):
    """Allow-list of {action_type, target_model, action_method} triples an
    AI-proposed action may execute immediately, without waiting for human
    approval - docs/architecture/21-copilot-rail-architecture.md §4's
    auto-executable tier. A narrow, deliberate, reviewed exception to
    CLAUDE.md §4 / hard risk #7's "no auto-execute path in v1" rule, not
    a reversal of it: only entries in this table, matched exactly on all
    three fields, are ever eligible - deployfleet.ai.action.request.
    propose() checks this table (plus its own data-category re-check)
    before ever bypassing the approval queue, and every other write
    still lands in pending_approval exactly as before this model existed.

    action_method is required, matching this tier's own reasoning: the
    doc's concrete starting examples (action_set_available(),
    action_confirm()) are all zero-arg state-transition methods, not
    plain field writes - a bare create/write auto-exec entry would need a
    much stronger reversibility argument than this tier is meant to
    carry.
    """

    _name = "deployfleet.ai.auto.executable.action"
    _description = "DeployFleet AI Auto-Executable Action Allow-List"
    _order = "action_type"

    action_type = fields.Char(required=True, help="Matches deployfleet.ai.action.request.action_type.")
    target_model = fields.Char(required=True)
    action_method = fields.Char(
        required=True,
        help="The zero-arg action_*() method this allow-list entry permits auto-executing.",
    )
    description = fields.Text(
        help="Why this specific action is safe to auto-execute - doc 21 §4's reversibility/"
             "cost criteria, not just 'seems fine'.",
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
