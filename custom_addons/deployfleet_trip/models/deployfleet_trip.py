from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetTrip(models.Model):
    """The execution-time record: planned vs. actual departure/arrival,
    odometer, delay reason. Created automatically when a
    deployfleet.dispatch.assignment is confirmed — see
    _handle_bus_event() below, subscribed via
    data/deployfleet_trip_event_subscriptions.xml rather than
    deployfleet_dispatch depending on this module directly (that would
    invert the dependency direction established in
    docs/architecture/04-module-structure.md).
    """

    _name = "deployfleet.trip"
    _description = "DeployFleet Trip"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    dispatch_assignment_id = fields.Many2one(
        "deployfleet.dispatch.assignment", required=True, ondelete="restrict"
    )
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    driver_id = fields.Many2one("hr.employee", required=True, domain=[("deployfleet_is_driver", "=", True)])
    route_id = fields.Many2one("deployfleet.route")
    planned_departure = fields.Datetime()
    planned_arrival = fields.Datetime()
    actual_departure = fields.Datetime()
    actual_arrival = fields.Datetime()
    odometer_start = fields.Float()
    odometer_end = fields.Float()
    delay_reason = fields.Char()
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("departed", "Departed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="planned",
        required=True,
    )
    shipment_line_ids = fields.One2many("deployfleet.trip.shipment.line", "trip_id", string="Shipments")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.trip")
        return super().create(vals_list)

    def action_depart(self):
        for trip in self:
            if trip.state != "planned":
                raise UserError(self.env._(
                    "Only a planned trip can depart - this one is '%(state)s'.", state=trip.state,
                ))
            trip.write({"actual_departure": fields.Datetime.now(), "state": "departed"})
            for line in trip.shipment_line_ids:
                if line.shipment_id.state == "assigned":
                    line.shipment_id.state = "in_transit"
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.trip.departed", "deployfleet.trip", trip.id,
                {"vehicle_id": trip.vehicle_id.id, "driver_id": trip.driver_id.id},
            )

    def action_complete(self, odometer_end=None):
        """Engineering-audit fix: this method had no state guard, so a
        double-click (or a client retry after a timeout where the write
        actually succeeded server-side) could re-fire deployfleet.trip.
        completed a second time - deployfleet_billing's own event handler
        has no existence check either, so a second fire created a fully
        independent second invoice, which then independently confirmed,
        posted to accounting, and independently submitted to ZRA. The
        state guard here is the primary fix; the billing side also gained
        a defense-in-depth existence check (see deployfleet_billing)."""
        for trip in self:
            if trip.state != "departed":
                raise UserError(self.env._(
                    "Only a departed trip can be completed - this one is '%(state)s'.", state=trip.state,
                ))
            vals = {"actual_arrival": fields.Datetime.now(), "state": "completed"}
            if odometer_end is not None:
                vals["odometer_end"] = odometer_end
            trip.write(vals)
            trip.vehicle_id.write({"status": "available", "current_driver_id": False})
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.trip.completed", "deployfleet.trip", trip.id,
                {"vehicle_id": trip.vehicle_id.id},
            )

    def action_report_delay(self, reason):
        for trip in self:
            trip.delay_reason = reason
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.trip.delayed", "deployfleet.trip", trip.id, {"reason": reason}
            )

    def action_cancel(self):
        for trip in self:
            if trip.state in ("completed", "cancelled"):
                raise UserError(self.env._(
                    "A %(state)s trip cannot be cancelled.", state=trip.state,
                ))
            # Engineering-audit fix: this write was previously
            # unconditional regardless of the trip's own state - cancelling
            # a stale trip record (a UI action fired against cached data,
            # or simply an old planned trip nobody got around to cancelling
            # before its vehicle moved on) could forcibly reset a vehicle
            # to "available" and clear its driver even if that vehicle is
            # currently mid-trip on a different, newer trip. The state
            # guard above rules out "completed"/"cancelled"; this check
            # additionally only releases the vehicle if THIS trip is
            # actually the one currently holding it - a "planned" trip
            # never took the vehicle in the first place (only
            # action_depart's own side effect does, indirectly via
            # action_confirm on the assignment), so releasing here is
            # only meaningful, and only safe, for a trip that's actually
            # "departed" and genuinely the vehicle's current occupant.
            still_this_trips_vehicle = trip.vehicle_id.current_trip_id == trip
            trip.state = "cancelled"
            if still_this_trips_vehicle:
                trip.vehicle_id.write({"status": "available", "current_driver_id": False})

    @api.model
    def _handle_bus_event(self, event_name, _source_model, source_id, _payload):
        """Event bus subscriber — see data/deployfleet_trip_event_subscriptions.xml.
        `_source_model`/`_payload` are part of the fixed handler contract
        (docs/architecture/02-reuse-strategy.md §0) but unused here."""
        if event_name != "deployfleet.dispatch.assigned":
            return None
        assignment = self.env["deployfleet.dispatch.assignment"].browse(source_id)
        if not assignment.exists():
            return None

        trip = self.create({
            "dispatch_assignment_id": assignment.id,
            "vehicle_id": assignment.vehicle_id.id,
            "driver_id": assignment.driver_id.id,
            "route_id": assignment.route_id.id if assignment.route_id else False,
            "planned_departure": assignment.planned_departure,
            "planned_arrival": assignment.planned_arrival,
        })
        self.env["deployfleet.trip.shipment.line"].create({
            "trip_id": trip.id,
            "shipment_id": assignment.shipment_id.id,
            "weight_portion_kg": assignment.shipment_id.weight_kg,
        })
        return trip
