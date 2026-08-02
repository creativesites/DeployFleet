from odoo import fields, models


class DeployfleetTripShipmentLine(models.Model):
    """The many-to-many join between trip and shipment — a trip can carry
    multiple shipments (consolidated cargo) and a shipment can require
    multiple trips (split loads). See
    docs/architecture/07-domain-model-erd.md §3: even in the common case
    of one shipment per trip, this join model costs nothing extra and
    avoids a schema change if multi-shipment trips turn out to be real.
    """

    _name = "deployfleet.trip.shipment.line"
    _description = "DeployFleet Trip-Shipment Line"

    trip_id = fields.Many2one("deployfleet.trip", required=True, ondelete="cascade")
    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="restrict")
    weight_portion_kg = fields.Float(help="This shipment's portion of the trip's total load.")

    _sql_constraints = [
        ("trip_shipment_unique", "UNIQUE(trip_id, shipment_id)", "This shipment is already on this trip."),
    ]
