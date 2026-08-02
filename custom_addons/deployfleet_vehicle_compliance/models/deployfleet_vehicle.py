from odoo import fields, models


class DeployfleetVehicle(models.Model):
    """Adds the vehicle-side view onto the polymorphic compliance engine
    from this module (not from deployfleet_vehicle itself), keeping the
    dependency one-way — deployfleet_vehicle has no knowledge of
    compliance documents."""

    _inherit = "deployfleet.vehicle"

    has_expired_compliance_documents = fields.Boolean(
        compute="_compute_has_expired_compliance_documents",
        help="True if any compliance document (insurance, roadworthiness, permit, "
             "registration) recorded for this vehicle is expired.",
    )

    def _compute_has_expired_compliance_documents(self):
        document_model = self.env["deployfleet.compliance.document"]
        for vehicle in self:
            vehicle.has_expired_compliance_documents = document_model.has_expired_documents(
                "deployfleet.vehicle", vehicle.id,
            )

    def action_view_compliance_documents(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Compliance Documents",
            "res_model": "deployfleet.compliance.document",
            "view_mode": "list,form",
            "domain": [("res_model", "=", "deployfleet.vehicle"), ("res_id", "=", self.id)],
            "context": {
                "default_res_model": "deployfleet.vehicle",
                "default_res_id": self.id,
            },
        }
