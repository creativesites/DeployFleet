from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetCalculationRule(TransactionCase):
    def setUp(self):
        super().setUp()
        self.rule_model = self.env["deployfleet.calculation.rule"]
        self.parameter_model = self.env["deployfleet.calculation.parameter"]

    def test_formula_computed_from_input_only(self):
        rule = self.rule_model.create({
            "key": "test_double",
            "name": "Test Double",
            "formula": "x * 2",
            "variable_ids": [(0, 0, {"name": "x", "source": "input"})],
        })
        self.assertEqual(rule.compute(inputs={"x": 21}), 42)

    def test_formula_computed_from_parameter(self):
        rule = self.rule_model.create({
            "key": "test_param",
            "name": "Test Param",
            "formula": "rate * 2",
            "variable_ids": [(0, 0, {"name": "rate", "source": "parameter"})],
        })
        self.parameter_model.create({"key": "rate", "name": "Rate", "value": 10.0})
        self.assertEqual(rule.compute(), 20.0)

    def test_missing_parameter_raises_user_error(self):
        rule = self.rule_model.create({
            "key": "test_missing_param",
            "name": "Test Missing Param",
            "formula": "rate * 2",
            "variable_ids": [(0, 0, {"name": "rate", "source": "parameter"})],
        })
        with self.assertRaises(UserError):
            rule.compute()

    def test_missing_input_raises_user_error(self):
        rule = self.rule_model.create({
            "key": "test_missing_input",
            "name": "Test Missing Input",
            "formula": "x * 2",
            "variable_ids": [(0, 0, {"name": "x", "source": "input"})],
        })
        with self.assertRaises(UserError):
            rule.compute()

    def test_vehicle_type_scoped_parameter_overrides_default(self):
        tanker = self.env.ref("deployfleet_core.vehicle_type_tanker")
        rule = self.rule_model.create({
            "key": "test_scoped",
            "name": "Test Scoped",
            "formula": "consumption",
            "variable_ids": [(0, 0, {"name": "consumption", "source": "parameter"})],
        })
        self.parameter_model.create({"key": "consumption", "name": "Consumption", "value": 30.0})
        self.parameter_model.create(
            {"key": "consumption", "name": "Consumption (Tanker)", "value": 45.0, "vehicle_type_id": tanker.id}
        )
        self.assertEqual(rule.compute(vehicle_type_id=tanker.id), 45.0)
        self.assertEqual(rule.compute(), 30.0)

    def test_formula_cannot_execute_arbitrary_code(self):
        rule = self.rule_model.create({
            "key": "test_unsafe",
            "name": "Test Unsafe",
            "formula": "__import__('os').system('echo unsafe')",
            "variable_ids": [],
        })
        with self.assertRaises(Exception):
            rule.compute()

    def test_invalid_variable_name_rejected(self):
        rule = self.rule_model.create({
            "key": "test_invalid_var",
            "name": "Test Invalid Var",
            "formula": "1",
        })
        with self.assertRaises(ValidationError):
            self.env["deployfleet.calculation.variable"].create({
                "rule_id": rule.id, "name": "not a valid name", "source": "input",
            })


@tagged("post_install", "-at_install")
class TestDeployfleetCalculatorSeedData(TransactionCase):
    def test_fuel_cost_rule_computes(self):
        rule = self.env.ref("deployfleet_freight_calculator.calc_rule_fuel_cost")
        result = rule.compute(inputs={"distance_km": 200.0})
        self.assertGreater(result, 0)

    def test_load_profit_rule_computes(self):
        rule = self.env.ref("deployfleet_freight_calculator.calc_rule_load_profit")
        result = rule.compute(inputs={
            "revenue": 5000.0, "tolls": 100.0, "fuel_cost": 500.0, "driver_cost": 500.0,
            "maintenance_allocation_cost": 300.0, "insurance_allocation_cost": 300.0,
            "depreciation_cost": 400.0,
        })
        self.assertEqual(result, 5000.0 - (100.0 + 500.0 + 500.0 + 300.0 + 300.0 + 400.0))


@tagged("post_install", "-at_install")
class TestDeployfleetFreightCalculatorWizard(TransactionCase):
    def test_fuel_calculator_produces_positive_result(self):
        wizard = self.env["deployfleet.freight.calculator.wizard"].create({
            "calculator_type": "fuel", "distance_km": 300.0,
        })
        wizard.action_compute()
        self.assertGreater(wizard.result, 0)
        self.assertEqual(wizard.result_label, "Fuel Cost")

    def test_load_profit_calculator_produces_result(self):
        wizard = self.env["deployfleet.freight.calculator.wizard"].create({
            "calculator_type": "load_profit", "distance_km": 300.0, "revenue": 5000.0, "tolls": 100.0,
        })
        wizard.action_compute()
        self.assertEqual(wizard.result_label, "Estimated Load Profit")

    def test_cost_per_km_requires_distance(self):
        wizard = self.env["deployfleet.freight.calculator.wizard"].create({
            "calculator_type": "cost_per_km", "revenue": 5000.0,
        })
        with self.assertRaises(UserError):
            wizard.action_compute()

    def test_break_even_calculator_produces_result(self):
        wizard = self.env["deployfleet.freight.calculator.wizard"].create({
            "calculator_type": "break_even", "distance_km": 300.0, "revenue": 5000.0,
        })
        wizard.action_compute()
        self.assertEqual(wizard.result_label, "Break-even Trips per Month")
