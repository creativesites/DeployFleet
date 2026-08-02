from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    deployfleet_active_license_id = fields.Many2one(
        "deployfleet.license",
        string="Active DeployFleet License",
        config_parameter="deployfleet_security.active_license_id",
    )
