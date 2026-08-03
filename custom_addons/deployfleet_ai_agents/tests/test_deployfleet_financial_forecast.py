from datetime import date

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetFinancialForecast(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Forecast Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Forecast Pickup"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Forecast Dropoff"})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id, "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id, "weight_kg": 100.0,
        })
        for month, amount in [(1, 1000.0), (2, 1200.0), (3, 1400.0)]:
            self.env["deployfleet.invoice"].create({
                "customer_id": self.customer.id,
                "invoice_date": date(2024, month, 15),
                "line_ids": [(0, 0, {
                    "shipment_id": self.shipment.id, "description": "Trip charge",
                    "quantity": 1.0, "unit_amount": amount,
                })],
            })

    def test_monthly_totals_groups_by_calendar_month(self):
        totals = self.env["deployfleet.financial.forecast"]._monthly_totals(
            "deployfleet.invoice", "invoice_date", "amount_total",
            [("customer_id", "=", self.customer.id)],
        )
        self.assertEqual(totals, [1000.0, 1200.0, 1400.0])

    def test_project_next_continues_a_rising_trend(self):
        forecast_model = self.env["deployfleet.financial.forecast"]
        projected = forecast_model._project_next([1000.0, 1200.0, 1400.0])
        self.assertAlmostEqual(projected, 1600.0)

    def test_project_next_with_single_month_repeats_it(self):
        forecast_model = self.env["deployfleet.financial.forecast"]
        self.assertEqual(forecast_model._project_next([500.0]), 500.0)

    def test_project_next_with_no_history_is_zero(self):
        forecast_model = self.env["deployfleet.financial.forecast"]
        self.assertEqual(forecast_model._project_next([]), 0.0)

    def test_compute_for_company_creates_forecast_record(self):
        forecast = self.env["deployfleet.financial.forecast"]._compute_for_company(self.env.company)
        self.assertEqual(forecast.company_id, self.env.company)
        self.assertAlmostEqual(forecast.forecast_revenue, 1600.0)
        self.assertEqual(forecast.months_of_history, 3)
