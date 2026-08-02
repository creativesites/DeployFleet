from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetVehicle(models.Model):
    """The DeployFleet operational layer over Odoo's native `fleet.vehicle`.

    Uses delegation inheritance (`_inherits`), not classical `_inherit` and
    not a standalone reinvention — see
    docs/architecture/03-refactoring-roadmap.md §A.2 and
    docs/architecture/06-risks-and-recommendations.md risk #2 for why this
    was the resolved decision. `fleet.vehicle`'s own fields (license plate,
    model, VIN, odometer, ...) stay reachable directly on this model
    (`my_vehicle.license_plate` just works) without this model needing to
    duplicate them.

    `current_trip_id` is deliberately NOT defined here — it's added by
    `deployfleet_trip` via `_inherit` once that module exists, keeping the
    dependency direction one-way (trip depends on vehicle, not vice versa).
    """

    _name = "deployfleet.vehicle"
    _description = "DeployFleet Vehicle Operational Profile"
    _inherits = {"fleet.vehicle": "fleet_vehicle_id"}
    _order = "id desc"

    fleet_vehicle_id = fields.Many2one(
        "fleet.vehicle", required=True, ondelete="cascade",
        help="The underlying Odoo Fleet vehicle record.",
    )
    status = fields.Selection(
        [
            ("available", "Available"),
            ("assigned", "Assigned"),
            ("maintenance", "Maintenance"),
            ("breakdown", "Breakdown"),
            ("retired", "Retired"),
        ],
        default="available",
        required=True,
    )
    vehicle_type_id = fields.Many2one("deployfleet.vehicle.type")
    current_driver_id = fields.Many2one(
        "hr.employee", domain=[("deployfleet_is_driver", "=", True)],
    )

    def action_set_available(self):
        self.write({"status": "available"})

    def action_set_maintenance(self):
        self.write({"status": "maintenance"})

    def action_set_breakdown(self):
        self.write({"status": "breakdown"})

    def action_set_retired(self):
        self.write({"status": "retired", "current_driver_id": False})

    @api.constrains("status", "current_driver_id")
    def _check_retired_has_no_driver(self):
        for vehicle in self:
            if vehicle.status == "retired" and vehicle.current_driver_id:
                raise ValidationError(
                    self.env._("A retired vehicle cannot have a current driver assigned.")
                )
