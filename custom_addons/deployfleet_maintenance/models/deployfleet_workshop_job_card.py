from odoo import fields, models


class DeployfleetWorkshopJobCard(models.Model):
    """Adds `maintenance_schedule_id` from this module (not from
    deployfleet_workshop itself) to keep the dependency one-way —
    deployfleet_workshop has no knowledge of maintenance scheduling."""

    _inherit = "deployfleet.workshop.job.card"

    maintenance_schedule_id = fields.Many2one(
        "deployfleet.maintenance.schedule",
        help="Set when this job card was opened from a maintenance-due alert.",
    )
