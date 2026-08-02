from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class DeployfleetPayrollRule(models.Model):
    """One payslip line's computation — country-neutral by design, per
    docs/architecture/03-refactoring-roadmap.md's fix for the source's
    payroll/country-pack coupling bug: 'deployfleet_payroll depends only
    on deployfleet_core/hr; country packs... register their rule sets
    via data, not via a manifest dependency chain.' This module owns the
    engine; deployfleet_l10n_zm (and future country packs) own the
    actual NAPSA/NHIMA/WCF/PAYE rule *data*.

    Same rule-engine shape as deployfleet_freight_calculator's
    calculation-rule engine (formula evaluated via safe_eval, never a
    bare eval()) — a deliberate parallel design, not shared code, since
    payroll and freight costing are different bounded contexts with
    different lifecycles.
    """

    _name = "deployfleet.payroll.rule"
    _description = "DeployFleet Payroll Rule"
    _order = "sequence, id"

    code = fields.Char(required=True, help="Stable identifier referenced by other rules, e.g. 'GROSS', 'PAYE'.")
    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    category = fields.Selection(
        [("gross", "Gross/Earnings"), ("deduction", "Deduction")],
        required=True,
        help="Determines whether this rule's amount adds to or subtracts from net pay.",
    )
    amount_type = fields.Selection(
        [("fixed", "Fixed Amount"), ("percentage", "Percentage of Another Rule"), ("formula", "Formula")],
        required=True, default="fixed",
    )
    amount_fixed = fields.Float()
    amount_percentage = fields.Float(help="Percentage value, e.g. 5 for 5%.")
    percentage_base_code = fields.Char(help="The rule code this percentage is computed against, e.g. 'GROSS'.")
    formula = fields.Char(help="Expression over previously computed rule codes, evaluated via safe_eval.")
    active = fields.Boolean(default=True)
    country_code = fields.Char(help="ISO country code this rule applies to. Blank = applies to every company.")

    _sql_constraints = [
        ("code_unique", "UNIQUE(code)", "Payroll rule codes must be unique."),
    ]

    def _compute_amount(self, context_values):
        self.ensure_one()
        if self.amount_type == "fixed":
            return self.amount_fixed
        if self.amount_type == "percentage":
            base = context_values.get(self.percentage_base_code, 0.0)
            return base * self.amount_percentage / 100.0
        if self.amount_type == "formula":
            return safe_eval(self.formula, context_values)
        return 0.0
