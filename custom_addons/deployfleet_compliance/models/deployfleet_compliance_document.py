from odoo import api, fields, models
from odoo.exceptions import ValidationError

EXPIRING_SOON_DAYS = 30


class DeployfleetComplianceDocument(models.Model):
    """One compliance document instance, polymorphically attached to any
    owner record via `res_model`/`res_id` (the same pattern
    `ir.attachment` uses) — the shared foundation both
    deployfleet_vehicle_compliance and a future driver-document module
    build on, per docs/architecture/02-reuse-strategy.md §1: 'both driver
    documents (license, medical) and vehicle documents (registration,
    insurance, roadworthiness) build on the same base.'

    `state` is a plain stored field, not a `compute=`, following the
    same pattern as deployfleet.license — a field that depends on
    "today" can't be kept correct by declarative @api.depends alone, so
    it's set explicitly on create/write and refreshed by a daily cron.
    """

    _name = "deployfleet.compliance.document"
    _description = "DeployFleet Compliance Document"
    _order = "expiry_date"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all. Polymorphic (res_model/res_id can point at either a
    # vehicle or a driver), so unlike most other C-01 instances this
    # can't be scoped via a relational domain against a single parent -
    # it needs its own column.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    document_type_id = fields.Many2one("deployfleet.compliance.document.type", required=True)
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    reference_number = fields.Char()
    issue_date = fields.Date()
    expiry_date = fields.Date()
    attachment = fields.Binary(attachment=True)
    verified = fields.Boolean(default=False)
    state = fields.Selection(
        [("valid", "Valid"), ("expiring_soon", "Expiring Soon"), ("expired", "Expired")],
        default="valid", required=True, copy=False,
    )

    @api.constrains("document_type_id", "expiry_date")
    def _check_expiry_required(self):
        for document in self:
            if document.document_type_id.requires_expiry and not document.expiry_date:
                raise ValidationError(
                    self.env._(
                        "'%(type)s' requires an expiry date.", type=document.document_type_id.name,
                    )
                )

    @api.model
    def _state_for_expiry(self, expiry_date):
        if not expiry_date:
            return "valid"
        today = fields.Date.today()
        if expiry_date < today:
            return "expired"
        if (expiry_date - today).days <= EXPIRING_SOON_DAYS:
            return "expiring_soon"
        return "valid"

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["state"] = self._state_for_expiry(vals.get("expiry_date"))
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if "expiry_date" in vals:
            for document in self:
                document.state = self._state_for_expiry(document.expiry_date)
        return res

    @api.model
    def _cron_refresh_states(self):
        for document in self.search([("expiry_date", "!=", False)]):
            new_state = self._state_for_expiry(document.expiry_date)
            if new_state != document.state:
                document.state = new_state

    @api.model
    def has_expired_documents(self, res_model, res_id):
        return bool(self.search_count([
            ("res_model", "=", res_model), ("res_id", "=", res_id), ("state", "=", "expired"),
        ]))

    @api.model
    def get_documents_for(self, res_model, res_id):
        return self.search([("res_model", "=", res_model), ("res_id", "=", res_id)])
