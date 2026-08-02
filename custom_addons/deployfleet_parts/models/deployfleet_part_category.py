from odoo import fields, models


class DeployfleetPartCategory(models.Model):
    _name = "deployfleet.part.category"
    _description = "DeployFleet Part Category"
    _order = "name"

    name = fields.Char(required=True)
    parent_id = fields.Many2one("deployfleet.part.category", ondelete="restrict")
