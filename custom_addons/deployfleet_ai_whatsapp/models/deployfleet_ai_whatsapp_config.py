from odoo import fields, models


class DeployfleetAIWhatsappConfig(models.Model):
    """Per-company WhatsApp Business (Meta Cloud API) credentials. One
    record per company, same pattern as `deployfleet.ai.config` and
    `deployfleet.zra.config`."""

    _name = "deployfleet.ai.whatsapp.config"
    _description = "DeployFleet WhatsApp Business Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    phone_number_id = fields.Char(required=True, help="Meta Cloud API phone number ID.")
    access_token = fields.Char(required=True, copy=False, help="Meta Cloud API access token.")
    webhook_verify_token = fields.Char(
        required=True,
        help="Shared secret Meta sends back during webhook verification (GET /api/whatsapp/webhook).",
    )
    enabled = fields.Boolean(default=True)

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Only one WhatsApp configuration per company."),
    ]
