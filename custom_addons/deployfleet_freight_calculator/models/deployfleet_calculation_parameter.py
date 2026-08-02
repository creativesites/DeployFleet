from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetCalculationParameter(models.Model):
    """Company-configurable value feeding a `deployfleet.calculation.rule`
    formula — see docs/architecture/14-freight-calculator-engine.md §3.

    Kept separate from the rule/formula itself so an admin can change
    "diesel price per litre" without anyone touching or re-reviewing the
    formula that uses it.
    """

    _name = "deployfleet.calculation.parameter"
    _description = "DeployFleet Calculation Parameter Value"

    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    key = fields.Char(required=True, help="e.g. 'diesel_price_per_l', 'maintenance_cost_per_km'.")
    name = fields.Char(required=True)
    value = fields.Float(required=True)
    vehicle_type_id = fields.Many2one(
        "deployfleet.vehicle.type",
        help="Optional — some parameters (fuel consumption) vary by vehicle type; "
             "leave blank for a company-wide default.",
    )

    _sql_constraints = [
        ("key_company_vehicle_type_unique", "UNIQUE(key, company_id, vehicle_type_id)",
         "A parameter with this key already exists for this company/vehicle type."),
    ]

    @api.model
    def _get_value(self, key, company=None, vehicle_type_id=None):
        company = company or self.env.company
        domain = [("key", "=", key), ("company_id", "=", company.id)]
        if vehicle_type_id:
            scoped = self.search(domain + [("vehicle_type_id", "=", vehicle_type_id)], limit=1)
            if scoped:
                return scoped.value
        default = self.search(domain + [("vehicle_type_id", "=", False)], limit=1)
        if not default:
            raise UserError(
                self.env._(
                    "No calculation parameter configured for key '%(key)s' on company %(company)s. "
                    "Configure it under DeployFleet > Configuration > Calculation Parameters.",
                    key=key, company=company.display_name,
                )
            )
        return default.value
