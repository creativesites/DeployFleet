from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
# The fixture chain (customer -> shipment -> assignment -> trip) mirrors a
# real dispatch flow end to end on purpose, one attribute per stage.
# pylint: disable=too-many-instance-attributes
class TestDeployfleetNotifications(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Notify Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Notify Pickup"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Notify Dropoff"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Notify Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Notify Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "NOTIFY-001", "model_id": model.id, "status": "available",
        })
        self.driver_user = self.env["res.users"].create({
            "name": "Notify Driver User", "login": "notify_driver@example.com",
            "email": "notify_driver@example.com",
        })
        self.driver = self.env["hr.employee"].create({
            "name": "Notify Driver", "deployfleet_is_driver": True, "user_id": self.driver_user.id,
        })
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
            "weight_kg": 500.0,
        })
        [self.assignment] = self.shipment.action_suggest_assignments(limit=1)

    def test_dispatch_assigned_notifies_driver(self):
        before = self.env["deployfleet.notification.log"].search_count([
            ("event_name", "=", "deployfleet.dispatch.assigned"),
        ])
        self.assignment.action_confirm()
        after = self.env["deployfleet.notification.log"].search_count([
            ("event_name", "=", "deployfleet.dispatch.assigned"),
        ])
        self.assertEqual(after, before + 1)

        log = self.env["deployfleet.notification.log"].search([
            ("event_name", "=", "deployfleet.dispatch.assigned"),
        ], limit=1, order="id desc")
        self.assertEqual(log.recipient_partner_id, self.driver_user.partner_id)
        self.assertEqual(log.state, "sent")

    def test_trip_delayed_notifies_customer_with_reason(self):
        self.assignment.action_confirm()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", self.assignment.id)])
        trip.action_report_delay("Road closure near Kabwe")

        log = self.env["deployfleet.notification.log"].search([
            ("event_name", "=", "deployfleet.trip.delayed"),
            ("recipient_partner_id", "=", self.customer.id),
        ], limit=1)
        self.assertTrue(log)
        self.assertIn("Road closure near Kabwe", log.message)

    def test_delivery_completed_notifies_customer(self):
        self.assignment.action_confirm()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", self.assignment.id)])
        trip.action_depart()
        self.env["deployfleet.delivery"].create({"trip_id": trip.id, "shipment_id": self.shipment.id})

        log = self.env["deployfleet.notification.log"].search([
            ("event_name", "=", "deployfleet.delivery.completed"),
            ("recipient_partner_id", "=", self.customer.id),
        ], limit=1)
        self.assertTrue(log)

    def test_unrelated_event_creates_no_notification(self):
        before = self.env["deployfleet.notification.log"].search_count([])
        self.env["deployfleet.event.log"].register_event(
            "unrelated.event.fired", "deployfleet.shipment", self.shipment.id
        )
        after = self.env["deployfleet.notification.log"].search_count([])
        self.assertEqual(before, after)
