from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetRateCard(models.Model):
    """The price a customer pays, as opposed to
    `deployfleet.calculation.rule` (deployfleet_freight_calculator), which
    is the company's internal cost estimate. The two are deliberately
    separate models — margin is the difference between them, not something
    either one computes on its own.
    """

    _name = "deployfleet.rate.card"
    _description = "DeployFleet Customer Rate Card"
    _order = "contract_id, vehicle_type_id"

    contract_id = fields.Many2one("deployfleet.contract", required=True, ondelete="cascade")
    rate_basis = fields.Selection(
        related="contract_id.rate_basis", store=True,
        help="Mirrors the parent contract's rate basis — a rate card only makes sense "
             "against the pricing model its contract already committed to.",
    )
    vehicle_type_id = fields.Many2one(
        "deployfleet.vehicle.type",
        help="Leave empty for a rate that applies regardless of vehicle type.",
    )
    unit_amount = fields.Monetary(required=True, string="Rate")
    currency_id = fields.Many2one(
        "res.currency", required=True, default=lambda self: self.env.company.currency_id
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "contract_vehicle_type_unique",
            "UNIQUE(contract_id, vehicle_type_id)",
            "Only one rate card per contract/vehicle-type combination.",
        ),
    ]

    @api.constrains("unit_amount")
    def _check_unit_amount_positive(self):
        for rate_card in self:
            if rate_card.unit_amount <= 0:
                raise ValidationError(self.env._("Rate card amounts must be positive."))

    @api.model
    def _get_rate(self, contract, vehicle_type=None):
        """Best-matching rate card for a contract: prefers one scoped to
        the given vehicle type, falls back to the type-agnostic one."""
        domain = [("contract_id", "=", contract.id)]
        if vehicle_type:
            scoped = self.search(domain + [("vehicle_type_id", "=", vehicle_type.id)], limit=1)
            if scoped:
                return scoped
        return self.search(domain + [("vehicle_type_id", "=", False)], limit=1)
