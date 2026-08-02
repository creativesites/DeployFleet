from odoo import models


class DeployfleetShipment(models.Model):
    """Adds portal.mixin so a customer's portal user gets a shareable
    access URL/token for their own shipment - the actual restriction to
    "their own" is enforced by the ir.rule in
    security/deployfleet_customer_portal_security.xml, not by this mixin
    (portal.mixin only provides the access-token machinery)."""

    _name = "deployfleet.shipment"
    _inherit = ["deployfleet.shipment", "portal.mixin"]

    # A compute method never returns a value by Odoo convention — it writes
    # straight to the field — so there is nothing to return here.
    # pylint: disable=missing-return
    def _compute_access_url(self):
        super()._compute_access_url()
        for shipment in self:
            shipment.access_url = f"/my/shipments/{shipment.id}"
