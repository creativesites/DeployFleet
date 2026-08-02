from odoo import fields, models
from odoo.exceptions import UserError


class DeployfleetFreightCalculatorWizard(models.TransientModel):
    """The user-facing surface over the calculation-rule engine — one
    wizard covering the calculators recommended for Phase 2 (see
    docs/architecture/14-freight-calculator-engine.md §4/§8): load
    profit, cost per km, break-even trips, fuel cost, trip time, and
    tyre cost per trip.
    """

    _name = "deployfleet.freight.calculator.wizard"
    _description = "DeployFleet Freight Calculator"

    calculator_type = fields.Selection(
        [
            ("load_profit", "Load Profit"),
            ("cost_per_km", "Cost per Km"),
            ("break_even", "Break-even Trips per Month"),
            ("fuel", "Fuel Cost"),
            ("trip_time", "Trip Time"),
            ("tyre_cost", "Tyre Cost per Trip"),
        ],
        required=True, default="load_profit",
    )
    vehicle_id = fields.Many2one("deployfleet.vehicle")
    distance_km = fields.Float()
    revenue = fields.Monetary()
    tolls = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    result = fields.Float(readonly=True)
    result_label = fields.Char(readonly=True)

    def _rule_value(self, key, **inputs):
        rule = self.env["deployfleet.calculation.rule"].search([("key", "=", key)], limit=1)
        if not rule:
            raise UserError(
                self.env._(
                    "No calculation rule configured for key '%(key)s'. "
                    "Check DeployFleet > Configuration > Calculation Rules.",
                    key=key,
                )
            )
        vehicle_type_id = self.vehicle_id.vehicle_type_id.id if self.vehicle_id else None
        return rule.compute(inputs=inputs, vehicle_type_id=vehicle_type_id, company=self.env.company)

    def action_compute(self):
        self.ensure_one()
        handler = getattr(self, f"_compute_{self.calculator_type}")
        value, label = handler()
        self.result = value
        self.result_label = label
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _compute_fuel(self):
        return self._rule_value("fuel_cost", distance_km=self.distance_km), self.env._("Fuel Cost")

    def _compute_tyre_cost(self):
        return self._rule_value("tyre_cost", distance_km=self.distance_km), self.env._("Tyre Cost")

    def _compute_trip_time(self):
        value = self._rule_value("trip_time_hours", distance_km=self.distance_km)
        return value, self.env._("Estimated Trip Time (hours)")

    def _compute_load_profit(self):
        fuel_cost = self._rule_value("fuel_cost", distance_km=self.distance_km)
        driver_cost = self._rule_value("driver_cost")
        maintenance_allocation_cost = self._rule_value("maintenance_allocation_cost", distance_km=self.distance_km)
        insurance_allocation_cost = self._rule_value("insurance_allocation_cost")
        depreciation_cost = self._rule_value("depreciation_cost", distance_km=self.distance_km)
        value = self._rule_value(
            "load_profit",
            revenue=self.revenue, tolls=self.tolls, fuel_cost=fuel_cost, driver_cost=driver_cost,
            maintenance_allocation_cost=maintenance_allocation_cost,
            insurance_allocation_cost=insurance_allocation_cost, depreciation_cost=depreciation_cost,
        )
        return value, self.env._("Estimated Load Profit")

    def _compute_cost_per_km(self):
        if not self.distance_km:
            raise UserError(self.env._("Distance (km) is required for the Cost per Km calculator."))
        fuel_cost = self._rule_value("fuel_cost", distance_km=self.distance_km)
        driver_cost = self._rule_value("driver_cost")
        maintenance_allocation_cost = self._rule_value("maintenance_allocation_cost", distance_km=self.distance_km)
        insurance_allocation_cost = self._rule_value("insurance_allocation_cost")
        depreciation_cost = self._rule_value("depreciation_cost", distance_km=self.distance_km)
        value = self._rule_value(
            "cost_per_km",
            fuel_cost=fuel_cost, driver_cost=driver_cost,
            maintenance_allocation_cost=maintenance_allocation_cost,
            insurance_allocation_cost=insurance_allocation_cost, depreciation_cost=depreciation_cost,
            distance_km=self.distance_km,
        )
        return value, self.env._("Cost per Km")

    def _compute_break_even(self):
        revenue_per_trip = self.revenue
        variable_cost_per_trip = (
            self._rule_value("fuel_cost", distance_km=self.distance_km)
            + self._rule_value("maintenance_allocation_cost", distance_km=self.distance_km)
            + self._rule_value("depreciation_cost", distance_km=self.distance_km)
        )
        value = self._rule_value(
            "break_even_trips_per_month",
            revenue_per_trip=revenue_per_trip, variable_cost_per_trip=variable_cost_per_trip,
        )
        return value, self.env._("Break-even Trips per Month")
