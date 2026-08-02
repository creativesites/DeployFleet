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
    max_weight_kg = fields.Float(
        help="Maximum cargo weight this vehicle can carry, in kg. Used for "
             "weight-aware dispatch scoring — see docs/architecture/12-ltl-freight-management-architecture.md §5.",
    )
    max_volume_m3 = fields.Float(help="Maximum cargo volume this vehicle can carry, in cubic meters.")
    gross_vehicle_weight_kg = fields.Float(
        string="Gross Vehicle Weight (kg)",
        help="Fully loaded weight limit (GVW). See docs/architecture/14-freight-calculator-engine.md §5.",
    )
    tare_weight_kg = fields.Float(string="Tare Weight (kg)", help="Empty (unloaded) vehicle weight.")
    payload_capacity_kg = fields.Float(
        compute="_compute_payload_capacity_kg", store=True,
        help="Gross vehicle weight minus tare weight — the maximum cargo weight before exceeding GVW.",
    )

    @api.depends("gross_vehicle_weight_kg", "tare_weight_kg")
    def _compute_payload_capacity_kg(self):
        for vehicle in self:
            vehicle.payload_capacity_kg = vehicle.gross_vehicle_weight_kg - vehicle.tare_weight_kg

    def action_set_available(self):
        self.write({"status": "available"})

    def action_set_maintenance(self):
        self.write({"status": "maintenance"})

    def action_set_breakdown(self):
        self.write({"status": "breakdown"})
        for vehicle in self:
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.vehicle.breakdown", "deployfleet.vehicle", vehicle.id,
                {"vehicle": vehicle.display_name, "driver_id": vehicle.current_driver_id.id},
            )

    def action_set_retired(self):
        self.write({"status": "retired", "current_driver_id": False})

    @api.constrains("status", "current_driver_id")
    def _check_retired_has_no_driver(self):
        for vehicle in self:
            if vehicle.status == "retired" and vehicle.current_driver_id:
                raise ValidationError(
                    self.env._("A retired vehicle cannot have a current driver assigned.")
                )
