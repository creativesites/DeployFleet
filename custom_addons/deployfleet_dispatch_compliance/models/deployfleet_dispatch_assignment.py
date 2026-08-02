from odoo import fields, models
from odoo.exceptions import UserError


class DeployfleetDispatchAssignment(models.Model):
    """Adds the emergency-override + audit-trail pattern for confirming
    an assignment despite an expired compliance document — see
    docs/architecture/06-risks-and-recommendations.md risk #3. The score
    hard-disqualify in deployfleet_shipment._score_candidate() already
    keeps non-compliant candidates out of `action_suggest_assignments()`
    entirely; this override exists for the rare case a dispatcher must
    confirm one anyway (e.g. no compliant vehicle is available and the
    load cannot wait) — every such confirmation is logged, never silent.
    """

    _inherit = "deployfleet.dispatch.assignment"

    compliance_override_reason = fields.Char(
        help="Required to confirm this assignment if the vehicle or driver has an expired compliance document.",
    )

    def _has_compliance_issue(self):
        self.ensure_one()
        document_model = self.env["deployfleet.compliance.document"]
        return (
            document_model.has_expired_documents("deployfleet.vehicle", self.vehicle_id.id)
            or document_model.has_expired_documents("hr.employee", self.driver_id.id)
        )

    def action_confirm(self):
        for assignment in self:
            if assignment._has_compliance_issue() and not assignment.compliance_override_reason:
                raise UserError(self.env._(
                    "The vehicle or driver on this assignment has an expired compliance document. "
                    "Provide a compliance override reason to confirm anyway."
                ))
        result = super().action_confirm()
        for assignment in self:
            if assignment.state == "confirmed" and assignment.compliance_override_reason:
                document_model = self.env["deployfleet.compliance.document"]
                self.env["deployfleet.dispatch.compliance.override.log"].create({
                    "assignment_id": assignment.id,
                    "reason": assignment.compliance_override_reason,
                    "vehicle_had_expired_documents": document_model.has_expired_documents(
                        "deployfleet.vehicle", assignment.vehicle_id.id,
                    ),
                    "driver_had_expired_documents": document_model.has_expired_documents(
                        "hr.employee", assignment.driver_id.id,
                    ),
                })
        return result
