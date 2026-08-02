from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetDelivery(TransactionCase):
    def setUp(self):
        super().setUp()
        customer = self.env["res.partner"].create({"name": "Test Customer"})
        pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.env["deployfleet.vehicle"].create({
            "license_plate": "POD-001", "model_id": model.id, "status": "available",
        })
        self.env["hr.employee"].create({"name": "POD Driver", "deployfleet_is_driver": True})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": customer.id, "pickup_depot_id": pickup.id, "dropoff_depot_id": dropoff.id,
        })
        [assignment] = self.shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        self.trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])

    def test_delivery_gets_auto_reference(self):
        delivery = self.env["deployfleet.delivery"].create({
            "trip_id": self.trip.id, "shipment_id": self.shipment.id, "recipient_name": "Jane Recipient",
        })
        self.assertTrue(delivery.name.startswith("POD"))

    def test_creating_delivery_marks_shipment_delivered(self):
        self.env["deployfleet.delivery"].create({"trip_id": self.trip.id, "shipment_id": self.shipment.id})
        self.assertEqual(self.shipment.state, "delivered")

    def test_shipment_must_be_on_the_trip(self):
        other_customer = self.env["res.partner"].create({"name": "Other Customer"})
        pickup = self.env["deployfleet.depot"].create({"name": "Other Pickup"})
        dropoff = self.env["deployfleet.depot"].create({"name": "Other Dropoff"})
        unrelated_shipment = self.env["deployfleet.shipment"].create({
            "customer_id": other_customer.id, "pickup_depot_id": pickup.id, "dropoff_depot_id": dropoff.id,
        })
        with self.assertRaises(ValidationError):
            self.env["deployfleet.delivery"].create({
                "trip_id": self.trip.id, "shipment_id": unrelated_shipment.id,
            })

    def test_duplicate_delivery_for_same_trip_shipment_is_blocked(self):
        self.env["deployfleet.delivery"].create({"trip_id": self.trip.id, "shipment_id": self.shipment.id})
        with self.assertRaises(Exception):
            self.env["deployfleet.delivery"].create({"trip_id": self.trip.id, "shipment_id": self.shipment.id})

    def test_delivery_publishes_completed_event(self):
        calls = []
        model_class = type(self.env["res.partner"])

        def _handler(_self, _event_name, _source_model, _source_id, payload):
            calls.append(payload)

        setattr(model_class, "_test_delivery_handler", _handler)
        self.addCleanup(delattr, model_class, "_test_delivery_handler")
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "deployfleet.delivery.completed",
            "model_name": "res.partner",
            "method_name": "_test_delivery_handler",
        })

        self.env["deployfleet.delivery"].create({"trip_id": self.trip.id, "shipment_id": self.shipment.id})
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["shipment_id"], self.shipment.id)
