from werkzeug.exceptions import NotFound

from odoo import http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.exceptions import AccessError
from odoo.http import request


class DeployfleetCustomerPortal(CustomerPortal):
    """Read-only portal views for a customer's own shipments, deliveries
    (proof of delivery), and invoices - the customer-facing proof this is
    a real operations platform, not just an internal tool (see
    docs/architecture/05-implementation-roadmap.md Phase 4)."""

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if "shipment_count" in counters:
            partner = request.env.user.partner_id
            values["shipment_count"] = request.env["deployfleet.shipment"].search_count([
                ("customer_id", "child_of", partner.commercial_partner_id.id),
            ])
        return values

    def _shipment_check_access(self, shipment_id):
        shipment = request.env["deployfleet.shipment"].browse([shipment_id])
        try:
            shipment.check_access("read")
        except AccessError as exc:
            raise NotFound() from exc
        return shipment.sudo()

    @http.route(["/my/shipments", "/my/shipments/page/<int:page>"], type="http", auth="user", website=True)
    def portal_my_shipments(self, page=1, **_kw):
        partner = request.env.user.partner_id
        shipment_model = request.env["deployfleet.shipment"]
        domain = [("customer_id", "child_of", partner.commercial_partner_id.id)]
        total = shipment_model.search_count(domain)
        pager_vals = portal_pager(url="/my/shipments", total=total, page=page, step=20)
        shipments = shipment_model.search(
            domain, limit=20, offset=pager_vals["offset"], order="create_date desc"
        )
        values = self._prepare_portal_layout_values()
        values.update({"shipments": shipments, "pager": pager_vals, "page_name": "shipment"})
        return request.render("deployfleet_customer_portal.portal_my_shipments", values)

    @http.route(["/my/shipments/<int:shipment_id>"], type="http", auth="user", website=True)
    def portal_shipment_detail(self, shipment_id, **_kw):
        shipment_sudo = self._shipment_check_access(shipment_id)
        deliveries = request.env["deployfleet.delivery"].sudo().search([
            ("shipment_id", "=", shipment_sudo.id),
        ])
        values = self._prepare_portal_layout_values()
        values.update({"shipment": shipment_sudo, "deliveries": deliveries})
        return request.render("deployfleet_customer_portal.portal_shipment_detail", values)
