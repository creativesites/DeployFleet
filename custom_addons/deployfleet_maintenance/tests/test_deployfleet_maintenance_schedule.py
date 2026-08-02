from datetime import date, timedelta

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetMaintenanceSchedule(TransactionCase):
    def setUp(self):
        super().setUp()
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "MNT-001", "model_id": model.id, "odometer": 50000.0,
        })

    def test_not_due_below_interval(self):
        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Oil Change",
            "interval_km": 10000.0, "last_service_odometer": 45000.0,
        })
        self.assertFalse(schedule.is_due)

    def test_due_when_odometer_reaches_threshold(self):
        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Oil Change",
            "interval_km": 5000.0, "last_service_odometer": 45000.0,
        })
        self.assertTrue(schedule.is_due)

    def test_due_when_calendar_interval_elapsed(self):
        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Annual Service",
            "interval_days": 30, "last_service_date": date.today() - timedelta(days=40),
        })
        self.assertTrue(schedule.is_due)

    def test_record_service_resets_due_and_notified(self):
        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Oil Change",
            "interval_km": 5000.0, "last_service_odometer": 45000.0,
        })
        self.assertTrue(schedule.is_due)
        schedule.due_notified = True
        schedule.action_record_service()
        self.assertFalse(schedule.is_due)
        self.assertFalse(schedule.due_notified)

    def test_cron_publishes_event_and_marks_notified(self):
        calls = []
        model_class = type(self.env["res.partner"])

        def _handler(_self, event_name, _source_model, _source_id, payload):
            calls.append((event_name, payload))

        setattr(model_class, "_test_maintenance_handler", _handler)
        self.addCleanup(delattr, model_class, "_test_maintenance_handler")
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "deployfleet.maintenance.due",
            "model_name": "res.partner",
            "method_name": "_test_maintenance_handler",
        })

        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Oil Change",
            "interval_km": 5000.0, "last_service_odometer": 45000.0,
        })
        self.env["deployfleet.maintenance.schedule"]._cron_notify_due_schedules()

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][0], "deployfleet.maintenance.due")
        self.assertTrue(schedule.due_notified)

        # Running the cron again must not re-notify.
        self.env["deployfleet.maintenance.schedule"]._cron_notify_due_schedules()
        self.assertEqual(len(calls), 1)

    def test_create_job_card_links_schedule(self):
        schedule = self.env["deployfleet.maintenance.schedule"].create({
            "vehicle_id": self.vehicle.id, "name": "Oil Change",
            "interval_km": 5000.0, "last_service_odometer": 45000.0,
        })
        job_card = schedule.action_create_job_card()
        self.assertEqual(job_card.maintenance_schedule_id, schedule)
        self.assertEqual(job_card.vehicle_id, self.vehicle)
