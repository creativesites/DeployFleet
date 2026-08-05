from odoo import fields, models


class DeployfleetHelpTag(models.Model):
    _name = "deployfleet.help.tag"
    _description = "DeployFleet Help Tag"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("name_unique", "UNIQUE(name)", "This tag already exists."),
    ]
