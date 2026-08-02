from odoo import fields, models


class DeployfleetLoadExpense(models.Model):
    """Adds `advance_id` from this module (not from deployfleet_load_expense
    itself) to keep the dependency one-way — deployfleet_load_expense has
    no knowledge of driver advances, per the same pattern used by
    deployfleet_trip adding current_trip_id to deployfleet.vehicle."""

    _inherit = "deployfleet.load.expense"

    advance_id = fields.Many2one(
        "deployfleet.driver.advance", string="Reconciled Against Advance",
        help="Set when this expense is being reconciled against a driver cash advance.",
    )
