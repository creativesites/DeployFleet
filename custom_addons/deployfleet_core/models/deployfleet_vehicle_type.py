from odoo import fields, models


class DeployfleetVehicleType(models.Model):
    """Shared master data: the kind of truck a driver is qualified to
    operate, and the kind a vehicle record is. Lives in the core module
    because both `deployfleet_driver` (qualifications) and
    `deployfleet_vehicle` (the vehicle's own type) need it, and neither
    should depend on the other just to share a tag list.
    """

    _name = "deployfleet.vehicle.type"
    _description = "DeployFleet Vehicle Type"
    _order = "sequence, name"

    name = fields.Char(required=True)
    code = fields.Char(help="Short code, e.g. 'rigid', 'articulated', 'tanker'.")
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("name_unique", "UNIQUE(name)", "Vehicle type name must be unique."),
    ]
