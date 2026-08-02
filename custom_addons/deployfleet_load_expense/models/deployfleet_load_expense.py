from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetLoadExpense(models.Model):
    """An actual cost incurred on a shipment/trip — see
    docs/architecture/15-load-sheet-architecture.md §5.

    This is the actuals-tracking companion to
    `deployfleet_freight_calculator`'s estimates: nothing before this
    module recorded what a load *actually* cost, only what it was
    predicted to cost.
    """

    _name = "deployfleet.load.expense"
    _description = "DeployFleet Load Expense"
    _order = "create_date desc"

    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="cascade")
    trip_id = fields.Many2one("deployfleet.trip")
    expense_type = fields.Selection(
        [
            ("fuel", "Fuel"),
            ("toll", "Toll"),
            ("loading_fee", "Loading/Offloading Fee"),
            ("permit", "Permit"),
            ("weighbridge", "Weighbridge Fee"),
            ("other", "Other"),
        ],
        required=True,
    )
    amount = fields.Monetary(required=True)
    currency_id = fields.Many2one("res.currency", required=True, default=lambda self: self.env.company.currency_id)
    recorded_by = fields.Many2one("res.users", default=lambda self: self.env.user)
    receipt = fields.Binary(attachment=True, help="Photo of the physical receipt.")

    @api.constrains("shipment_id", "trip_id")
    def _check_shipment_is_on_trip(self):
        for expense in self:
            if expense.trip_id and expense.shipment_id not in expense.trip_id.shipment_line_ids.shipment_id:
                raise ValidationError(self.env._("This shipment is not on the selected trip."))
