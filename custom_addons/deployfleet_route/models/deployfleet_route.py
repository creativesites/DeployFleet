from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetRoute(models.Model):
    _name = "deployfleet.route"
    _description = "DeployFleet Route"
    _order = "name"

    name = fields.Char(required=True, help="e.g. 'Lusaka -> Kitwe'.")
    origin_depot_id = fields.Many2one("deployfleet.depot", required=True, string="Origin")
    destination_depot_id = fields.Many2one("deployfleet.depot", required=True, string="Destination")
    distance_km = fields.Float(string="Distance (km)")
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    stop_ids = fields.One2many("deployfleet.route.stop", "route_id", string="Stops")
    active = fields.Boolean(default=True)

    @api.constrains("origin_depot_id", "destination_depot_id")
    def _check_origin_destination_differ(self):
        for route in self:
            if route.origin_depot_id == route.destination_depot_id:
                raise ValidationError(self.env._("Origin and destination depots must be different."))


class DeployfleetRouteStop(models.Model):
    _name = "deployfleet.route.stop"
    _description = "DeployFleet Route Stop"
    _order = "route_id, sequence"

    route_id = fields.Many2one("deployfleet.route", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    depot_id = fields.Many2one("deployfleet.depot", required=True)
