from odoo import fields, models


class DeployfleetAsset(models.Model):
    """A non-vehicle trackable asset — trailer, container, GPS tracker,
    tool, safety equipment — see docs/architecture/04-module-structure.md.

    Deliberately independent of deployfleet_vehicle (per that document's
    dependency list: deployfleet_core only) — 'location' is free text
    rather than a vehicle reference, so this module doesn't need to wait
    on or couple to the vehicle domain to be useful.
    """

    _name = "deployfleet.asset"
    _description = "DeployFleet Asset"
    _order = "name"

    name = fields.Char(required=True)
    asset_type = fields.Selection(
        [
            ("trailer", "Trailer"),
            ("container", "Container"),
            ("gps_tracker", "GPS Tracker"),
            ("tool", "Tool"),
            ("safety_equipment", "Safety Equipment"),
            ("other", "Other"),
        ],
        required=True,
    )
    serial_number = fields.Char()
    status = fields.Selection(
        [
            ("in_service", "In Service"),
            ("in_storage", "In Storage"),
            ("under_repair", "Under Repair"),
            ("retired", "Retired"),
        ],
        default="in_service", required=True,
    )
    location = fields.Char(help="Free-text current location, e.g. a depot name or 'with Truck ABC-123'.")
    acquisition_date = fields.Date()
    notes = fields.Text()

    def action_set_in_service(self):
        self.write({"status": "in_service"})

    def action_set_in_storage(self):
        self.write({"status": "in_storage"})

    def action_set_under_repair(self):
        self.write({"status": "under_repair"})

    def action_set_retired(self):
        self.write({"status": "retired"})
