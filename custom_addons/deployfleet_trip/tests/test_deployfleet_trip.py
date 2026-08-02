from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DeployfleetTripTestBase(TransactionCase):
    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Test Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        self.vehicle = self.env["deployfleet.vehicle"].create({
            "license_plate": "TRIP-001", "model_id": model.id, "status": "available",
        })
        self.driver = self.env["hr.employee"].create({"name": "Trip Driver", "deployfleet_is_driver": True})
        self.shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
            "weight_kg": 500.0,
        })

    def _confirm_an_assignment(self):
        [assignment] = self.shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        return assignment


class TestDeployfleetTripCreation(DeployfleetTripTestBase):
    def test_confirming_assignment_creates_trip_via_event_bus(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        self.assertEqual(len(trip), 1)
        self.assertEqual(trip.vehicle_id, self.vehicle)
        self.assertEqual(trip.driver_id, self.driver)
        self.assertEqual(trip.state, "planned")

    def test_trip_creation_creates_shipment_line(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        self.assertEqual(len(trip.shipment_line_ids), 1)
        self.assertEqual(trip.shipment_line_ids.shipment_id, self.shipment)
        self.assertEqual(trip.shipment_line_ids.weight_portion_kg, 500.0)

    def test_trip_gets_auto_reference(self):
        self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([], limit=1, order="create_date desc")
        self.assertTrue(trip.name.startswith("TRP"))

    def test_unrelated_event_does_not_create_a_trip(self):
        before = self.env["deployfleet.trip"].search_count([])
        self.env["deployfleet.event.log"].register_event(
            "vehicle.breakdown.created", "deployfleet.vehicle", self.vehicle.id
        )
        after = self.env["deployfleet.trip"].search_count([])
        self.assertEqual(before, after)


class TestDeployfleetTripWorkflow(DeployfleetTripTestBase):
    def test_depart_sets_actual_departure_and_shipment_in_transit(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_depart()
        self.assertEqual(trip.state, "departed")
        self.assertTrue(trip.actual_departure)
        self.assertEqual(self.shipment.state, "in_transit")

    def test_complete_frees_vehicle(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_depart()
        trip.action_complete(odometer_end=1234.5)
        self.assertEqual(trip.state, "completed")
        self.assertEqual(trip.odometer_end, 1234.5)
        self.assertEqual(self.vehicle.status, "available")
        self.assertFalse(self.vehicle.current_driver_id)

    def test_current_trip_on_vehicle_reflects_active_trip(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        self.assertEqual(self.vehicle.current_trip_id, trip)
        trip.action_depart()
        self.assertEqual(self.vehicle.current_trip_id, trip)
        trip.action_complete()
        self.assertFalse(self.vehicle.current_trip_id)

    def test_report_delay_sets_reason(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_report_delay("Road closure near Kabwe")
        self.assertEqual(trip.delay_reason, "Road closure near Kabwe")
