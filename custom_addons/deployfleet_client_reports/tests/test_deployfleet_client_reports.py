from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
# The fixture chain (customer -> shipment -> trip -> delivery -> invoice ->
# wizard) mirrors a real dispatch-to-billing flow end to end on purpose,
# one attribute per stage — collapsing them would just hide the flow.
# pylint: disable=too-many-instance-attributes
class TestDeployfleetClientReportWizard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Report Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Report Pickup"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Report Dropoff"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Report Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Report Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "RPT-001", "model_id": model.id, "status": "available",
        })
        self.driver = self.env["hr.employee"].create({"name": "Report Driver", "deployfleet_is_driver": True})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
            "weight_kg": 500.0,
            "requested_pickup_date": fields.Datetime.now(),
        })
        [assignment] = self.shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        self.trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        self.trip.action_depart()
        self.trip.action_complete()
        self.env["deployfleet.delivery"].create({
            "trip_id": self.trip.id, "shipment_id": self.shipment.id,
        })
        self.invoice = self.env["deployfleet.invoice"].create({
            "customer_id": self.customer.id,
            "line_ids": [
                (0, 0, {
                    "shipment_id": self.shipment.id,
                    "description": "Trip charge", "quantity": 1.0, "unit_amount": 1000.0,
                }),
            ],
        })
        self.wizard = self.env["deployfleet.client.report.wizard"].create({
            "customer_id": self.customer.id,
            "date_from": fields.Date.today().replace(day=1),
            "date_to": fields.Date.today(),
        })

    def test_get_shipments_returns_delivered_shipment(self):
        shipments = self.wizard._get_shipments()
        self.assertEqual(shipments, self.shipment)

    def test_get_invoices_returns_invoice_in_range(self):
        invoices = self.wizard._get_invoices()
        self.assertEqual(invoices, self.invoice)

    def test_get_on_time_rate_counts_completed_trip(self):
        self.assertEqual(self.wizard._get_on_time_rate(), 100.0)

    def test_get_total_billed_sums_invoice_amounts(self):
        self.assertEqual(self.wizard._get_total_billed(), 1000.0)

    def test_no_shipments_outside_date_range(self):
        wizard = self.env["deployfleet.client.report.wizard"].create({
            "customer_id": self.customer.id,
            "date_from": fields.Date.today().replace(day=1) - timedelta(days=60),
            "date_to": fields.Date.today().replace(day=1) - timedelta(days=31),
        })
        self.assertFalse(wizard._get_shipments())
