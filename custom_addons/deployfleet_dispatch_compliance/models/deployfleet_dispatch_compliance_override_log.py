from odoo import fields, models


class DeployfleetDispatchComplianceOverrideLog(models.Model):
    """The audit trail for every emergency compliance override — see
    docs/architecture/06-risks-and-recommendations.md risk #3: this is a
    dedicated, queryable record rather than relying solely on the
    generic event bus log, given the regulatory/safety stakes."""

    _name = "deployfleet.dispatch.compliance.override.log"
    _description = "DeployFleet Dispatch Compliance Override Log"
    _order = "create_date desc"

    assignment_id = fields.Many2one("deployfleet.dispatch.assignment", required=True, ondelete="cascade")
    reason = fields.Char(required=True)
    overridden_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    vehicle_had_expired_documents = fields.Boolean()
    driver_had_expired_documents = fields.Boolean()
