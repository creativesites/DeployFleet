from odoo import fields, models


class DeployfleetLeaveType(models.Model):
    _name = "deployfleet.leave.type"
    _description = "DeployFleet Leave Type"
    _order = "name"

    name = fields.Char(required=True)
    default_days_per_year = fields.Float(default=0.0)
    requires_approval = fields.Boolean(default=True)
