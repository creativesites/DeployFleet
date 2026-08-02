from odoo import fields, models


class DeployfleetClientReportWizard(models.TransientModel):
    """Entry point for a per-customer PDF summary: shipments delivered,
    on-time trip performance, and billing, all over an explicit date
    range. A wizard rather than a stored report configuration - there is
    nothing here worth persisting between runs."""

    _name = "deployfleet.client.report.wizard"
    _description = "DeployFleet Client Report Wizard"

    customer_id = fields.Many2one("res.partner", required=True)
    date_from = fields.Date(required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date(required=True, default=fields.Date.today)

    def action_print_report(self):
        self.ensure_one()
        return self.env.ref("deployfleet_client_reports.action_report_client_summary").report_action(self)

    def _get_shipments(self):
        self.ensure_one()
        return self.env["deployfleet.shipment"].search([
            ("customer_id", "=", self.customer_id.id),
            ("state", "=", "delivered"),
            ("requested_pickup_date", ">=", self.date_from),
            ("requested_pickup_date", "<=", self.date_to),
        ])

    def _get_invoices(self):
        self.ensure_one()
        return self.env["deployfleet.invoice"].search([
            ("customer_id", "=", self.customer_id.id),
            ("invoice_date", ">=", self.date_from),
            ("invoice_date", "<=", self.date_to),
            ("state", "!=", "cancelled"),
        ])

    def _get_completed_trips(self):
        self.ensure_one()
        shipment_ids = self._get_shipments().ids
        lines = self.env["deployfleet.trip.shipment.line"].search([("shipment_id", "in", shipment_ids)])
        return lines.trip_id.filtered(lambda trip: trip.state == "completed")

    def _get_on_time_rate(self):
        trips = self._get_completed_trips()
        if not trips:
            return 0.0
        on_time = trips.filtered(
            lambda trip: not trip.planned_arrival or not trip.actual_arrival
            or trip.actual_arrival <= trip.planned_arrival
        )
        return round(100.0 * len(on_time) / len(trips), 1)

    def _get_total_billed(self):
        invoices = self._get_invoices()
        return sum(invoices.mapped("amount_total"))
