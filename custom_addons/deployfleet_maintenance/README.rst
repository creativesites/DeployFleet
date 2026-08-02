=========================
DeployFleet Maintenance
=========================

Odometer- and/or calendar-based preventive service schedules
(``deployfleet.maintenance.schedule``) per
``docs/architecture/04-module-structure.md``. A daily cron
(``_cron_notify_due_schedules``) publishes ``deployfleet.maintenance.due``
on the event bus for any schedule that's newly due, without re-notifying
every day until ``action_record_service()`` resets it.

``action_create_job_card()`` opens a ``deployfleet.workshop.job.card``
directly from a due schedule (linked via ``maintenance_schedule_id``,
added to that model from this module to keep the dependency one-way) —
the literal Phase 2 exit criterion from
``docs/architecture/05-implementation-roadmap.md``: "a job card can be
opened from a maintenance-due alert."
