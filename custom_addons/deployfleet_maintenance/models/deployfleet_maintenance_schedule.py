from datetime import timedelta

from odoo import api, fields, models


class DeployfleetMaintenanceSchedule(models.Model):
    """A preventive-service plan for one vehicle — odometer- and/or
    calendar-based — see docs/architecture/04-module-structure.md:
    'odometer/engine-hour/calendar preventive service scheduling;
    publishes deployfleet.maintenance.due.'

    `due_notified` exists so the daily cron doesn't republish the same
    due event every day until the service is actually recorded —
    `action_record_service()` is what resets it.
    """

    _name = "deployfleet.maintenance.schedule"
    _description = "DeployFleet Maintenance Schedule"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    name = fields.Char(required=True, help="e.g. 'Oil Change', 'Full Service'.")
    interval_km = fields.Float(help="0 = not odometer-based.")
    interval_days = fields.Integer(help="0 = not calendar-based.")
    last_service_odometer = fields.Float()
    last_service_date = fields.Date()
    next_due_odometer = fields.Float(compute="_compute_next_due", store=True)
    next_due_date = fields.Date(compute="_compute_next_due", store=True)
    is_due = fields.Boolean(compute="_compute_is_due", store=True)
    due_notified = fields.Boolean(default=False, copy=False)

    @api.depends("interval_km", "interval_days", "last_service_odometer", "last_service_date")
    def _compute_next_due(self):
        for schedule in self:
            schedule.next_due_odometer = (
                schedule.last_service_odometer + schedule.interval_km if schedule.interval_km else 0.0
            )
            schedule.next_due_date = (
                schedule.last_service_date + timedelta(days=schedule.interval_days)
                if schedule.interval_days and schedule.last_service_date else False
            )

    @api.depends("next_due_odometer", "next_due_date", "vehicle_id.odometer")
    def _compute_is_due(self):
        today = fields.Date.context_today(self)
        for schedule in self:
            due_by_odometer = bool(
                schedule.interval_km and schedule.vehicle_id.odometer >= schedule.next_due_odometer
            )
            due_by_date = bool(schedule.interval_days and schedule.next_due_date and today >= schedule.next_due_date)
            schedule.is_due = due_by_odometer or due_by_date

    def action_record_service(self, odometer=None, date=None):
        for schedule in self:
            schedule.write({
                "last_service_odometer": odometer if odometer is not None else schedule.vehicle_id.odometer,
                "last_service_date": date or fields.Date.context_today(schedule),
                "due_notified": False,
            })

    def action_create_job_card(self):
        self.ensure_one()
        return self.env["deployfleet.workshop.job.card"].create({
            "vehicle_id": self.vehicle_id.id,
            "description": self.name,
            "maintenance_schedule_id": self.id,
        })

    @api.model
    def _cron_notify_due_schedules(self):
        due_schedules = self.search([("is_due", "=", True), ("due_notified", "=", False)])
        for schedule in due_schedules:
            self.env["deployfleet.event.log"].register_event(
                "deployfleet.maintenance.due", "deployfleet.maintenance.schedule", schedule.id,
                {"vehicle_id": schedule.vehicle_id.id, "schedule_name": schedule.name},
            )
            schedule.due_notified = True
