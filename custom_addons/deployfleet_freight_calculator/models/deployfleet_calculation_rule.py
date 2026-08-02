from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class DeployfleetCalculationRule(models.Model):
    """A named formula over `deployfleet.calculation.variable`s — see
    docs/architecture/14-freight-calculator-engine.md §3.

    Formulas are evaluated exclusively via `safe_eval`, never a bare
    `eval()`/`exec()` — the formula is company-editable data, so it must
    be treated as untrusted input evaluated in a restricted sandbox, the
    same way Odoo core treats domains and server actions.
    """

    _name = "deployfleet.calculation.rule"
    _description = "DeployFleet Freight Calculation Rule"

    key = fields.Char(required=True, help="Stable identifier, e.g. 'fuel_cost', 'depreciation_cost'.")
    name = fields.Char(required=True)
    formula = fields.Char(
        required=True,
        help="Expression over named variables, e.g. "
             "'(distance_km / consumption_l_per_100km * 100) * diesel_price_per_l'.",
    )
    variable_ids = fields.One2many("deployfleet.calculation.variable", "rule_id")

    _sql_constraints = [
        ("key_unique", "UNIQUE(key)", "Calculation rule keys must be unique."),
    ]

    def compute(self, inputs=None, vehicle_type_id=None, company=None):
        """Resolves every declared variable (from `inputs` if provided at
        call time, otherwise from `deployfleet.calculation.parameter`) and
        evaluates `formula` against them via `safe_eval`."""
        self.ensure_one()
        inputs = inputs or {}
        company = company or self.env.company
        parameter_model = self.env["deployfleet.calculation.parameter"]

        values = {}
        for variable in self.variable_ids:
            if variable.name in inputs:
                values[variable.name] = inputs[variable.name]
            elif variable.source == "parameter":
                values[variable.name] = parameter_model._get_value(
                    variable.parameter_key or variable.name,
                    company=company, vehicle_type_id=vehicle_type_id,
                )
            else:
                raise UserError(
                    self.env._(
                        "Calculation rule '%(rule)s' requires an input value for '%(variable)s'.",
                        rule=self.name, variable=variable.name,
                    )
                )
        return safe_eval(self.formula, values)


class DeployfleetCalculationVariable(models.Model):
    """One named variable a `deployfleet.calculation.rule`'s formula
    references, and where its value comes from."""

    _name = "deployfleet.calculation.variable"
    _description = "DeployFleet Calculation Rule Variable"

    rule_id = fields.Many2one("deployfleet.calculation.rule", required=True, ondelete="cascade")
    name = fields.Char(required=True, help="The variable name as used inside the formula, e.g. 'distance_km'.")
    source = fields.Selection(
        [("parameter", "Company Parameter"), ("input", "Provided at call time")],
        required=True, default="parameter",
    )
    parameter_key = fields.Char(
        help="deployfleet.calculation.parameter key to look up when source is 'Company Parameter'. "
             "Defaults to the variable name itself if left blank.",
    )

    @api.constrains("name")
    def _check_name_is_valid_identifier(self):
        for variable in self:
            if not variable.name.isidentifier():
                raise ValidationError(
                    self.env._(
                        "'%(name)s' is not a valid variable name — it must be a plain identifier "
                        "(letters, digits, underscores, not starting with a digit).",
                        name=variable.name,
                    )
                )
