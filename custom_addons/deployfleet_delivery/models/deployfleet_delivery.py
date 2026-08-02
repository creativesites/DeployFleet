from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetDelivery(models.Model):
    """Proof of delivery for one shipment on one trip. Per
    docs/architecture/07-domain-model-erd.md, keyed to (trip, shipment)
    rather than just (trip), because a multi-drop trip carrying several
    shipments produces one delivery per drop, each with its own POD.

    Creating a delivery record is the completion event — it immediately
    marks the shipment `delivered` and publishes
    `deployfleet.delivery.completed`. It deliberately does NOT complete the
    trip itself (a multi-stop trip may still have other shipments in
    transit) — the driver/dispatcher calls `deployfleet.trip.action_complete()`
    separately once the whole run is done.

    `gps_stamp` is free-text "lat,long" for Phase 1 — a real GPS
    integration is explicitly a later phase
    (docs/architecture/05-implementation-roadmap.md, "Beyond Phase 5").
    """

    _name = "deployfleet.delivery"
    _description = "DeployFleet Proof of Delivery"
    _order = "delivered_at desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    trip_id = fields.Many2one("deployfleet.trip", required=True, ondelete="restrict")
    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="restrict")
    delivered_at = fields.Datetime(default=fields.Datetime.now, required=True)
    recipient_name = fields.Char()
    signature = fields.Binary(attachment=True)
    photo = fields.Binary(attachment=True)
    gps_stamp = fields.Char(help="Free-text 'lat,long' for Phase 1 — see class docstring.")

    _sql_constraints = [
        ("trip_shipment_unique", "UNIQUE(trip_id, shipment_id)",
         "A delivery already exists for this shipment on this trip."),
    ]

    @api.constrains("shipment_id", "trip_id")
    def _check_shipment_is_on_trip(self):
        for delivery in self:
            if delivery.shipment_id not in delivery.trip_id.shipment_line_ids.shipment_id:
                raise ValidationError(self.env._("This shipment is not on the selected trip."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.delivery")
        deliveries = super().create(vals_list)
        for delivery in deliveries:
            delivery.shipment_id.state = "delivered"
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.delivery.completed", "deployfleet.delivery", delivery.id,
                {"shipment_id": delivery.shipment_id.id, "trip_id": delivery.trip_id.id},
            )
        return deliveries
