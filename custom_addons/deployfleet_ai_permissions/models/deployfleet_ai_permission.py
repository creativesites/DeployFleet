from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetAIPermission(models.Model):
    """Per-role AI feature access, per
    docs/architecture/08-ai-architecture.md §9: "can this role ask this
    *kind* of question" - a coarser, different concern from Odoo's own
    model-level ACLs, and one nothing in deployfleet_ai_core enforces on
    its own.

    Opt-in by feature: a `deployfleet.ai.feature` with no permission rows
    at all is open to every authenticated user (unchanged from
    deployfleet_ai_core's pre-existing behavior) - creating even one row
    for a feature turns it into an explicit allow-list for that feature
    only, so adding role gating to a new feature never requires touching
    this module's code.

    Row-level scoping ("a driver may query the Dispatch Agent about their
    own trips, not the whole company's") is deliberately NOT implemented
    as a generic engine here - see README.rst. It is enforced per-feature
    by whatever code builds that feature's query (the same way
    deployfleet_mobile_dispatcher/customer already query as the logged-in
    user, never sudo(), so ir.rule naturally scopes the result set).
    """

    _name = "deployfleet.ai.permission"
    _description = "DeployFleet AI Feature Permission"

    feature_id = fields.Many2one("deployfleet.ai.feature", required=True, ondelete="cascade")
    group_id = fields.Many2one("res.groups", required=True)

    _sql_constraints = [
        (
            "feature_group_unique", "UNIQUE(feature_id, group_id)",
            "This group already has a permission row for this feature.",
        ),
    ]

    @api.model
    def _check_user_allowed(self, user, feature_key):
        """Raises UserError if `user` may not use the AI feature identified
        by `feature_key`. Called from deployfleet.ai.core.complete() via
        this module's _inherit - see deployfleet_ai_core.py in this
        module."""
        feature = self.env["deployfleet.ai.feature"].search([("key", "=", feature_key)], limit=1)
        if not feature:
            return  # deployfleet_ai_core.complete() itself raises for an unknown/disabled feature
        permissions = self.search([("feature_id", "=", feature.id)])
        if not permissions:
            return  # no rows configured for this feature - open to everyone, see class docstring
        if not user.groups_id & permissions.group_id:
            raise UserError(
                self.env._(
                    "You do not have permission to use the AI feature '%(feature)s'.",
                    feature=feature.name,
                )
            )
