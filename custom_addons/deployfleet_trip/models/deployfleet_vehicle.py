from odoo import fields, models


class DeployfleetVehicle(models.Model):
    """Adds `current_trip_id` to `deployfleet.vehicle` — deliberately not
    defined in deployfleet_vehicle itself, so that module's dependency
    graph never has to know deployfleet_trip exists. See
    docs/architecture/03-refactoring-roadmap.md and the docstring on
    deployfleet_vehicle's own model for the reasoning.
    """

    _inherit = "deployfleet.vehicle"

    current_trip_id = fields.Many2one("deployfleet.trip", compute="_compute_current_trip")

    def _compute_current_trip(self):
        trip_model = self.env["deployfleet.trip"]
        for vehicle in self:
            trip = trip_model.search(
                [("vehicle_id", "=", vehicle.id), ("state", "in", ("planned", "departed"))],
                limit=1, order="create_date desc",
            )
            vehicle.current_trip_id = trip.id if trip else False
