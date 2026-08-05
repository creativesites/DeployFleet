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

    def action_close(self):
        """Engineering-audit fix: closing a job card opened from a
        maintenance-due alert never reset the schedule it came from -
        next_due_odometer/next_due_date are computed off
        last_service_odometer/last_service_date, which action_record_service()
        is the only thing that updates. Without this, is_due stayed True
        (or flipped back True on the very next cron run) forever after the
        service was actually done, since due_notified only suppresses a
        second notification, it doesn't affect is_due itself."""
        result = super().action_close()
        for job_card in self:
            if job_card.maintenance_schedule_id:
                job_card.maintenance_schedule_id.action_record_service(
                    odometer=job_card.vehicle_id.odometer,
                    date=job_card.closed_date,
                )
        return result
