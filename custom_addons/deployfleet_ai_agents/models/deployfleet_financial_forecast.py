from odoo import api, fields, models

from ..lib import stats


class DeployfleetFinancialForecast(models.Model):
    """Financial forecasting: least-squares trend projection over monthly
    revenue (`deployfleet.invoice`) and fuel cost (`deployfleet.fuel.log`)
    aggregates - see docs/architecture/05-implementation-roadmap.md Phase
    5. A forecast, not a budget target: it reads history, it does not
    prescribe one, and with only a couple of months of seed data behind
    it, treat the number as illustrative until real operational history
    accumulates - see README.rst."""

    _name = "deployfleet.financial.forecast"
    _description = "DeployFleet Financial Forecast"
    _order = "computed_date desc"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    computed_date = fields.Datetime(default=fields.Datetime.now, required=True)
    months_of_history = fields.Integer()
    forecast_revenue = fields.Monetary()
    forecast_fuel_cost = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    basis = fields.Text()

    @api.model
    def _monthly_totals(self, model_name, date_field, amount_field, domain):
        records = self.env[model_name].search(domain)
        buckets = {}
        for record in records:
            date_value = record[date_field]
            if not date_value:
                continue
            key = (date_value.year, date_value.month)
            buckets[key] = buckets.get(key, 0.0) + record[amount_field]
        return [buckets[key] for key in sorted(buckets)]

    @api.model
    def _project_next(self, monthly_totals):
        if not monthly_totals:
            return 0.0
        if len(monthly_totals) < 2:
            return monthly_totals[-1]
        xs = list(range(len(monthly_totals)))
        slope, intercept = stats.linear_regression(xs, monthly_totals)
        return max(slope * len(monthly_totals) + intercept, 0.0)

    @api.model
    def _compute_for_company(self, company=None):
        company = company or self.env.company
        revenue_totals = self._monthly_totals(
            "deployfleet.invoice", "invoice_date", "amount_total",
            [("company_id", "=", company.id), ("state", "!=", "cancelled")],
        )
        fuel_totals = self._monthly_totals(
            "deployfleet.fuel.log", "date", "total_cost",
            [("vehicle_id.company_id", "=", company.id)],
        )

        return self.create({
            "company_id": company.id,
            "months_of_history": max(len(revenue_totals), len(fuel_totals)),
            "forecast_revenue": self._project_next(revenue_totals),
            "forecast_fuel_cost": self._project_next(fuel_totals),
            "basis": (
                f"Projected from {len(revenue_totals)} month(s) of invoice history and "
                f"{len(fuel_totals)} month(s) of fuel log history using a linear trend."
            ),
        })

    @api.model
    def _cron_compute_all_companies(self):
        for company in self.env["res.company"].search([]):  # pylint: disable=no-search-all
            self._compute_for_company(company)
