from odoo import fields, models


class DeployfleetComplianceDocumentType(models.Model):
    """Master data: what kind of compliance document exists, and which
    polymorphic owner model it applies to (e.g. 'hr.employee' for a
    driver's license, 'deployfleet.vehicle' for insurance)."""

    _name = "deployfleet.compliance.document.type"
    _description = "DeployFleet Compliance Document Type"
    _order = "name"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    applies_to_model = fields.Char(
        required=True,
        help="Technical model name this document type applies to, e.g. 'hr.employee' or 'deployfleet.vehicle'.",
    )
    requires_expiry = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Document type code must be unique."),
    ]
