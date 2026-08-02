from odoo import fields, models


class DeployfleetTyreReading(models.Model):
    """A tread-depth measurement over time for one tyre."""

    _name = "deployfleet.tyre.reading"
    _description = "DeployFleet Tyre Tread Depth Reading"
    _order = "date desc, id desc"

    tyre_id = fields.Many2one("deployfleet.tyre", required=True, ondelete="cascade")
    date = fields.Date(default=fields.Date.context_today, required=True)
    tread_depth_mm = fields.Float(required=True)
    odometer = fields.Float()
