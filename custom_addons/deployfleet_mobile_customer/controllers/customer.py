from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.deployfleet_core.controllers.mobile_api import (
    envelope_success,
    require_authenticated,
)
from odoo.exceptions import AccessError
from odoo.http import request


class DeployfleetMobileCustomerController(http.Controller):
    """REST API backing the customer mobile app: shipment tracking,
    delivery status, and invoices (see
    docs/architecture/04-module-structure.md's mobile app table). Row-level
    access is enforced by the ir.rule records in deployfleet_customer_portal
    (scoped to the caller's own commercial partner), not by anything in
    this controller - every query here runs as the logged-in user, never
    sudo, so that restriction always applies."""

    @http.route("/api/mobile/customer/shipments", type="http", auth="user", methods=["GET"], csrf=False)
    @require_authenticated
    def shipments(self, **_kw):
        shipments = request.env["deployfleet.shipment"].search([], order="create_date desc", limit=100)
        data = [self._serialize_shipment(shipment) for shipment in shipments]
        return request.make_json_response(envelope_success(data))

    @http.route(
        "/api/mobile/customer/shipments/<int:shipment_id>", type="http", auth="user", methods=["GET"], csrf=False
    )
    @require_authenticated
    def shipment_detail(self, shipment_id, **_kw):
        shipment = request.env["deployfleet.shipment"].browse(shipment_id)
        try:
            shipment.check_access("read")
        except AccessError as exc:
            raise NotFound() from exc

        deliveries = request.env["deployfleet.delivery"].search([("shipment_id", "=", shipment.id)])
        data = self._serialize_shipment(shipment)
        data["deliveries"] = [
            {
                "id": delivery.id,
                "delivered_at": str(delivery.delivered_at),
                "recipient_name": delivery.recipient_name,
                "has_signature": bool(delivery.signature),
                "has_photo": bool(delivery.photo),
            }
            for delivery in deliveries
        ]
        return request.make_json_response(envelope_success(data))

    @http.route("/api/mobile/customer/invoices", type="http", auth="user", methods=["GET"], csrf=False)
    @require_authenticated
    def invoices(self, **_kw):
        invoices = request.env["deployfleet.invoice"].search([], order="invoice_date desc", limit=100)
        data = [
            {
                "id": invoice.id,
                "name": invoice.name,
                "invoice_date": str(invoice.invoice_date),
                "state": invoice.state,
                "amount_total": invoice.amount_total,
            }
            for invoice in invoices
        ]
        return request.make_json_response(envelope_success(data))

    def _serialize_shipment(self, shipment):
        return {
            "id": shipment.id,
            "name": shipment.name,
            "state": shipment.state,
            "pickup": shipment.pickup_depot_id.name,
            "dropoff": shipment.dropoff_depot_id.name,
            "cargo_description": shipment.cargo_description,
        }
