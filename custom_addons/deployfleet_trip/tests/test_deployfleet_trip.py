from odoo.exceptions import UserError
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

    def test_depart_requires_planned_state(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_depart()
        with self.assertRaises(UserError):
            trip.action_depart()

    def test_complete_requires_departed_state(self):
        """Regression test for an engineering-audit finding:
        action_complete() had no state guard, so a double-click (or a
        client retry after a timeout where the write actually succeeded
        server-side) could re-fire deployfleet.trip.completed a second
        time - deployfleet_billing's own event handler had no existence
        check either, so a second fire created a fully independent
        second invoice."""
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        # Not yet departed.
        with self.assertRaises(UserError):
            trip.action_complete()
        trip.action_depart()
        trip.action_complete()
        with self.assertRaises(UserError):
            trip.action_complete()

    def test_cancel_completed_trip_raises(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_depart()
        trip.action_complete()
        with self.assertRaises(UserError):
            trip.action_cancel()

    def test_cancel_releases_vehicle_when_this_trip_is_its_current_one(self):
        assignment = self._confirm_an_assignment()
        trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", assignment.id)])
        trip.action_cancel()
        self.assertEqual(trip.state, "cancelled")
        self.assertEqual(self.vehicle.status, "available")
        self.assertFalse(self.vehicle.current_driver_id)

    def test_cancel_stale_trip_does_not_release_a_newer_trips_vehicle(self):
        """Regression test for an engineering-audit finding:
        action_cancel() previously reset the vehicle to available and
        cleared its driver unconditionally, regardless of whether THIS
        trip was actually the vehicle's current one - cancelling a stale
        trip record still sitting in "planned"/"departed" state could
        silently interrupt a different, newer trip already under way on
        the same vehicle.

        The normal dispatch -> confirm -> depart -> complete flow can no
        longer produce two simultaneously "planned"/"departed" trips on
        one vehicle at all: action_confirm()'s own vehicle-availability
        guard (see test_confirming_a_vehicle_already_committed_elsewhere_
        raises in deployfleet_dispatch) refuses to confirm a second
        assignment against a vehicle that isn't "available", and the only
        way a trip's vehicle returns to "available" is action_complete/
        action_cancel, both of which move that trip OUT of
        ("planned", "departed") - so the precondition this guard defends
        against can no longer arise through the public API. This test
        constructs it directly via the ORM instead, simulating a stale/
        inconsistent data scenario, to verify the still_this_trips_vehicle
        defense-in-depth check independently of that structural fix."""
        old_assignment = self._confirm_an_assignment()
        old_trip = self.env["deployfleet.trip"].search([("dispatch_assignment_id", "=", old_assignment.id)])
        old_trip.action_depart()
        self.assertEqual(self.vehicle.status, "assigned")

        # A second trip is created directly against the same vehicle,
        # bypassing action_confirm() (which would correctly refuse this
        # while the vehicle is still "assigned") to simulate a stale
        # data scenario rather than a reachable user flow.
        new_shipment = self.env["deployfleet.shipment"].create({
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
            "weight_kg": 200.0,
        })
        new_assignment = self.env["deployfleet.dispatch.assignment"].create({
            "shipment_id": new_shipment.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "state": "confirmed",
        })
        new_trip = self.env["deployfleet.trip"].create({
            "dispatch_assignment_id": new_assignment.id,
            "vehicle_id": self.vehicle.id,
            "driver_id": self.driver.id,
            "state": "planned",
        })
        # Force new_trip to sort after old_trip by create_date, so
        # _compute_current_trip() resolves it as the vehicle's current
        # trip - deterministic instead of relying on wall-clock timing.
        self.env.cr.execute(
            "UPDATE deployfleet_trip SET create_date = create_date + interval '1 second' WHERE id = %s",
            (new_trip.id,),
        )
        new_trip.invalidate_recordset(["create_date"])
        self.assertEqual(self.vehicle.current_trip_id, new_trip)

        # Cancelling the stale OLD trip (still "departed", but no longer
        # the vehicle's current occupant) must succeed - it's a valid
        # state transition - but must NOT release the vehicle out from
        # under the new trip.
        old_trip.action_cancel()
        self.assertEqual(old_trip.state, "cancelled")
        self.assertEqual(self.vehicle.status, "assigned")
        self.assertEqual(self.vehicle.current_driver_id, self.driver)
        self.assertEqual(self.vehicle.current_trip_id, new_trip)
