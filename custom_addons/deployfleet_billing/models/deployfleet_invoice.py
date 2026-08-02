from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetInvoice(models.Model):
    """The DeployFleet-domain billable document: what a customer owes for a
    trip, computed from `deployfleet.rate.card`. Deliberately independent
    of `account.move` — `deployfleet_accounting` (which depends on this
    module, not the other way around) is what turns a confirmed one of
    these into a real accounting entry, keeping the pricing domain usable
    even for a company that hasn't wired up accounting yet.
    """

    _name = "deployfleet.invoice"
    _description = "DeployFleet Invoice"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    customer_id = fields.Many2one("res.partner", required=True)
    contract_id = fields.Many2one("deployfleet.contract")
    trip_id = fields.Many2one("deployfleet.trip", ondelete="restrict")
    invoice_date = fields.Date(required=True, default=fields.Date.today)
    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    state = fields.Selection(
        [("draft", "Draft"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        default="draft",
        required=True,
    )
    line_ids = fields.One2many("deployfleet.invoice.line", "invoice_id")
    amount_total = fields.Monetary(compute="_compute_amount_total", store=True)

    @api.depends("line_ids.subtotal")
    def _compute_amount_total(self):
        for invoice in self:
            invoice.amount_total = sum(invoice.line_ids.mapped("subtotal"))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.invoice")
        return super().create(vals_list)

    def action_confirm(self):
        for invoice in self:
            if invoice.state != "draft":
                continue
            if not invoice.line_ids:
                raise UserError(self.env._("Cannot confirm an invoice with no lines."))
            invoice.state = "confirmed"
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.invoice.confirmed", "deployfleet.invoice", invoice.id,
                {"customer_id": invoice.customer_id.id, "amount_total": invoice.amount_total},
            )

    def action_cancel(self):
        self.write({"state": "cancelled"})

    @api.model
    def _handle_bus_event(self, event_name, _source_model, source_id, _payload):
        """Event bus subscriber — see
        data/deployfleet_billing_event_subscriptions.xml. Fires when a trip
        completes; bills whichever shipments on that trip have a contract
        with a matching rate card. A shipment with no contract, or a
        contract with no rate card yet, is silently left off the invoice —
        that's a spot load or an incomplete pricing setup, not an error the
        trip-completion flow should ever block on."""
        if event_name != "deployfleet.trip.completed":
            return None
        trip = self.env["deployfleet.trip"].browse(source_id)
        if not trip.exists():
            return None

        rate_card_model = self.env["deployfleet.rate.card"]
        lines_by_customer = {}
        for shipment_line in trip.shipment_line_ids:
            shipment = shipment_line.shipment_id
            if not shipment.contract_id:
                continue
            rate_card = rate_card_model._get_rate(shipment.contract_id, trip.vehicle_id.vehicle_type_id)
            if not rate_card:
                continue
            quantity = shipment_line.weight_portion_kg if rate_card.rate_basis == "per_tonnage" else 1.0
            if rate_card.rate_basis == "per_distance":
                quantity = trip.route_id.distance_km or 1.0
            lines_by_customer.setdefault(shipment.customer_id, []).append({
                "shipment_id": shipment.id,
                "description": shipment.name,
                "quantity": quantity,
                "unit_amount": rate_card.unit_amount,
            })

        created = self.browse()
        for customer, line_vals in lines_by_customer.items():
            invoice = self.create({
                "customer_id": customer.id,
                "contract_id": trip.shipment_line_ids[:1].shipment_id.contract_id.id,
                "trip_id": trip.id,
                "line_ids": [(0, 0, vals) for vals in line_vals],
            })
            created |= invoice
        return created


class DeployfleetInvoiceLine(models.Model):
    _name = "deployfleet.invoice.line"
    _description = "DeployFleet Invoice Line"

    invoice_id = fields.Many2one("deployfleet.invoice", required=True, ondelete="cascade")
    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="restrict")
    description = fields.Char(required=True)
    quantity = fields.Float(required=True, default=1.0)
    unit_amount = fields.Monetary(required=True)
    currency_id = fields.Many2one(related="invoice_id.currency_id", store=True)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)

    @api.depends("quantity", "unit_amount")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_amount
