from odoo import api, fields, models
from odoo.exceptions import ValidationError


class DeployfleetWorkshopJobLine(models.Model):
    """One labor or parts line on a job card."""

    _name = "deployfleet.workshop.job.line"
    _description = "DeployFleet Workshop Job Line"

    job_card_id = fields.Many2one("deployfleet.workshop.job.card", required=True, ondelete="cascade")
    line_type = fields.Selection([("labor", "Labor"), ("part", "Part")], required=True, default="labor")
    part_id = fields.Many2one("deployfleet.part")
    description = fields.Char()
    quantity = fields.Float(default=1.0, required=True)
    unit_cost = fields.Monetary()
    currency_id = fields.Many2one(related="job_card_id.currency_id", store=True)
    subtotal = fields.Monetary(compute="_compute_subtotal", store=True)

    @api.depends("quantity", "unit_cost")
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.unit_cost

    @api.constrains("line_type", "part_id")
    def _check_part_required_for_part_lines(self):
        for line in self:
            if line.line_type == "part" and not line.part_id:
                raise ValidationError(self.env._("A part line must reference a part."))
