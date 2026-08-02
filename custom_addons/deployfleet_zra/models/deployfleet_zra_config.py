from odoo import fields, models


class DeployfleetZRAConfig(models.Model):
    """Per-company ZRA Smart Invoice (VSDC) device registration.

    Field names (tpin/bhfId/dvcSrlNo) match the Device Initialization
    request in ZRA's official VSDC API Specification, cross-checked
    against the community-maintained Postman collection at
    github.com/williemwewa/vsdc_api_postman_collection (ZRA's own PDF spec
    returned HTTP 503 when this module was written and could not be
    fetched directly) - confirm against the current spec/sandbox before
    going live, especially the base URL, which ZRA issues per-device and
    isn't published anywhere generic.
    """

    _name = "deployfleet.zra.config"
    _description = "DeployFleet ZRA Smart Invoice Device Configuration"
    _rec_name = "company_id"

    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company, index=True
    )
    environment = fields.Selection(
        [("sandbox", "Sandbox"), ("production", "Production")],
        default="sandbox",
        required=True,
    )
    base_url = fields.Char(
        required=True,
        help="Host issued by ZRA for this device/environment - not a generic published URL.",
    )
    tpin = fields.Char(string="TPIN", required=True, help="Company's Taxpayer Identification Number.")
    branch_id = fields.Char(string="Branch ID (bhfId)", default="000", required=True)
    device_serial_no = fields.Char(string="Device Serial No (dvcSrlNo)", required=True)
    default_vat_category_code = fields.Char(
        default="A",
        help="ZRA VAT category code applied to every invoice line by default "
             "(A = standard-rated). Review with someone qualified on ZRA VAT "
             "categories before relying on this for real submissions - "
             "deployfleet_invoice.line has no per-line tax category of its own yet.",
    )
    device_api_key = fields.Char(copy=False, help="Security key returned by ZRA on device initialization.")
    initialized = fields.Boolean(default=False, copy=False)

    _sql_constraints = [
        ("company_unique", "UNIQUE(company_id)", "Only one ZRA device configuration per company."),
    ]

    def action_initialize_device(self):
        self.ensure_one()
        self.env["deployfleet.zra.client"]._device_init(self)
