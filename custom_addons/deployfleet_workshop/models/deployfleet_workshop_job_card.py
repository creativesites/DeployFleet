from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetWorkshopJobCard(models.Model):
    """Open -> diagnose -> repair (labor + parts) -> approve -> close —
    see docs/architecture/04-module-structure.md.
    """

    _name = "deployfleet.workshop.job.card"
    _description = "DeployFleet Workshop Job Card"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    description = fields.Char()
    opened_date = fields.Date(default=fields.Date.context_today, required=True)
    closed_date = fields.Date()
    state = fields.Selection(
        [
            ("open", "Open"),
            ("diagnosis", "Diagnosis"),
            ("repair", "Repair"),
            ("approval", "Pending Approval"),
            ("closed", "Closed"),
        ],
        default="open", required=True,
    )
    line_ids = fields.One2many("deployfleet.workshop.job.line", "job_card_id")
    total_cost = fields.Monetary(compute="_compute_total_cost", store=True)
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.workshop.job.card")
        return super().create(vals_list)

    @api.depends("line_ids.subtotal")
    def _compute_total_cost(self):
        for job_card in self:
            job_card.total_cost = sum(job_card.line_ids.mapped("subtotal"))

    def _check_state(self, expected):
        for job_card in self:
            if job_card.state != expected:
                raise UserError(
                    self.env._(
                        "Job card '%(name)s' must be in state '%(expected)s' for this action, not '%(actual)s'.",
                        name=job_card.name, expected=expected, actual=job_card.state,
                    )
                )

    def action_start_diagnosis(self):
        self._check_state("open")
        self.write({"state": "diagnosis"})

    def action_start_repair(self):
        self._check_state("diagnosis")
        for job_card in self:
            job_card.state = "repair"
            job_card.vehicle_id.action_set_maintenance()

    def action_submit_for_approval(self):
        self._check_state("repair")
        self.write({"state": "approval"})

    def action_close(self):
        self._check_state("approval")
        for job_card in self:
            for line in job_card.line_ids.filtered(lambda ln: ln.line_type == "part"):
                line.part_id.action_consume_stock(line.quantity)
            job_card.write({"state": "closed", "closed_date": fields.Date.context_today(job_card)})
            job_card.vehicle_id.action_set_available()
