from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class DeployfleetDispatchTestBase(TransactionCase):
    def _create_vehicle(self, **extra):
        model = self.env["fleet.vehicle.model"].search([], limit=1)
        if not model:
            brand = self.env["fleet.vehicle.model.brand"].create({"name": "Test Brand"})
            model = self.env["fleet.vehicle.model"].create({"name": "Test Model", "brand_id": brand.id})
        vals = {"license_plate": f"TEST-{self.env['ir.sequence'].next_by_code('deployfleet.shipment') or '0'}",
                "model_id": model.id, "status": "available"}
        vals.update(extra)
        return self.env["deployfleet.vehicle"].create(vals)

    def _create_driver(self, **extra):
        vals = {"name": "Test Driver", "deployfleet_is_driver": True}
        vals.update(extra)
        return self.env["hr.employee"].create(vals)

    def setUp(self):
        super().setUp()
        self.customer = self.env["res.partner"].create({"name": "Test Customer"})
        self.pickup = self.env["deployfleet.depot"].create({"name": "Pickup Depot"})
        self.dropoff = self.env["deployfleet.depot"].create({"name": "Dropoff Depot"})

    def _create_shipment(self, **extra):
        vals = {
            "customer_id": self.customer.id,
            "pickup_depot_id": self.pickup.id,
            "dropoff_depot_id": self.dropoff.id,
        }
        vals.update(extra)
        return self.env["deployfleet.shipment"].create(vals)


class TestDeployfleetShipment(DeployfleetDispatchTestBase):
    def test_shipment_gets_auto_reference(self):
        shipment = self._create_shipment()
        self.assertTrue(shipment.name.startswith("SHP"))

    def test_pickup_and_dropoff_must_differ(self):
        with self.assertRaises(UserError):
            self._create_shipment(dropoff_depot_id=self.pickup.id)

    def test_confirm_transitions_draft_to_confirmed(self):
        shipment = self._create_shipment()
        self.assertEqual(shipment.state, "draft")
        shipment.action_confirm()
        self.assertEqual(shipment.state, "confirmed")


class TestDeployfleetScoring(DeployfleetDispatchTestBase):
    def test_unavailable_vehicle_is_disqualified(self):
        vehicle = self._create_vehicle(status="maintenance")
        driver = self._create_driver()
        shipment = self._create_shipment()
        self.assertIsNone(shipment._score_candidate(vehicle, driver))

    def test_wrong_vehicle_type_is_disqualified(self):
        tanker = self.env.ref("deployfleet_core.vehicle_type_tanker")
        rigid = self.env.ref("deployfleet_core.vehicle_type_rigid")
        vehicle = self._create_vehicle(vehicle_type_id=rigid.id)
        driver = self._create_driver()
        shipment = self._create_shipment(required_vehicle_type_id=tanker.id)
        self.assertIsNone(shipment._score_candidate(vehicle, driver))

    def test_matching_vehicle_type_is_not_disqualified(self):
        rigid = self.env.ref("deployfleet_core.vehicle_type_rigid")
        vehicle = self._create_vehicle(vehicle_type_id=rigid.id)
        driver = self._create_driver()
        shipment = self._create_shipment(required_vehicle_type_id=rigid.id)
        self.assertIsNotNone(shipment._score_candidate(vehicle, driver))

    def test_overweight_shipment_is_disqualified(self):
        vehicle = self._create_vehicle(max_weight_kg=10000.0)
        driver = self._create_driver()
        shipment = self._create_shipment(weight_kg=15000.0)
        self.assertIsNone(shipment._score_candidate(vehicle, driver))

    def test_shipment_within_weight_limit_is_not_disqualified(self):
        vehicle = self._create_vehicle(max_weight_kg=10000.0)
        driver = self._create_driver()
        shipment = self._create_shipment(weight_kg=8000.0)
        self.assertIsNotNone(shipment._score_candidate(vehicle, driver))

    def test_vehicle_with_no_max_weight_set_is_never_weight_disqualified(self):
        vehicle = self._create_vehicle()
        driver = self._create_driver()
        shipment = self._create_shipment(weight_kg=50000.0)
        self.assertIsNotNone(shipment._score_candidate(vehicle, driver))

    def test_experience_increases_score_and_accidents_decrease_it(self):
        vehicle = self._create_vehicle()
        shipment = self._create_shipment()
        experienced = self._create_driver(name="Experienced", deployfleet_years_experience=10)
        rookie = self._create_driver(name="Rookie", deployfleet_years_experience=0)
        risky = self._create_driver(name="Risky", deployfleet_accident_count=3)

        self.assertGreater(shipment._score_candidate(vehicle, experienced), shipment._score_candidate(vehicle, rookie))
        self.assertGreater(shipment._score_candidate(vehicle, rookie), shipment._score_candidate(vehicle, risky))


class TestDeployfleetSuggestAssignments(DeployfleetDispatchTestBase):
    def test_suggest_assignments_creates_proposed_records_ranked_by_score(self):
        self._create_vehicle()
        self._create_driver(name="Best", deployfleet_years_experience=10)
        self._create_driver(name="Worst", deployfleet_accident_count=5)
        shipment = self._create_shipment()

        created = shipment.action_suggest_assignments(limit=5)
        self.assertEqual(len(created), 2)
        self.assertTrue(all(a.state == "proposed" for a in created))
        scores = created.mapped("score")
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_suggest_assignments_respects_limit(self):
        self._create_vehicle()
        for i in range(5):
            self._create_driver(name=f"Driver {i}")
        shipment = self._create_shipment()
        created = shipment.action_suggest_assignments(limit=2)
        self.assertEqual(len(created), 2)

    def test_rerunning_suggestions_clears_previous_proposals(self):
        self._create_vehicle()
        self._create_driver()
        shipment = self._create_shipment()
        first_batch = shipment.action_suggest_assignments(limit=5)
        shipment.action_suggest_assignments(limit=5)
        self.assertFalse(first_batch.exists())


class TestDeployfleetAssignmentConfirm(DeployfleetDispatchTestBase):
    def test_confirm_top_candidate_without_override_reason(self):
        self._create_vehicle()
        self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()  # should not raise
        self.assertEqual(assignment.state, "confirmed")

    def test_confirming_lower_scored_candidate_requires_override_reason(self):
        self._create_vehicle()
        self._create_driver(name="Best", deployfleet_years_experience=10)
        self._create_driver(name="Worst", deployfleet_accident_count=5)
        shipment = self._create_shipment()
        created = shipment.action_suggest_assignments(limit=5)
        worst = min(created, key=lambda a: a.score)

        with self.assertRaises(UserError):
            worst.action_confirm()

        worst.override_reason = "Best driver unavailable on-site."
        worst.action_confirm()
        self.assertEqual(worst.state, "confirmed")

    def test_confirming_sets_vehicle_assigned_and_shipment_assigned(self):
        vehicle = self._create_vehicle()
        driver = self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        self.assertEqual(vehicle.status, "assigned")
        self.assertEqual(vehicle.current_driver_id, driver)
        self.assertEqual(shipment.state, "assigned")

    def test_confirming_cancels_sibling_proposals(self):
        self._create_vehicle()
        self._create_driver(name="Best", deployfleet_years_experience=10)
        self._create_driver(name="Second", deployfleet_years_experience=5)
        shipment = self._create_shipment()
        created = shipment.action_suggest_assignments(limit=5)
        best = max(created, key=lambda a: a.score)
        best.action_confirm()
        others = created - best
        self.assertTrue(all(a.state == "cancelled" for a in others))

    def test_cancel_confirmed_assignment_frees_vehicle(self):
        vehicle = self._create_vehicle()
        self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        assignment.action_cancel()
        self.assertEqual(vehicle.status, "available")
        self.assertFalse(vehicle.current_driver_id)
        self.assertEqual(shipment.state, "confirmed")

    def test_confirm_publishes_dispatch_assigned_event(self):
        calls = []
        model_class = type(self.env["res.partner"])

        def _handler(_self, event_name, _source_model, _source_id, payload):
            calls.append((event_name, payload))

        setattr(model_class, "_test_dispatch_handler", _handler)
        self.addCleanup(delattr, model_class, "_test_dispatch_handler")
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "deployfleet.dispatch.assigned",
            "model_name": "res.partner",
            "method_name": "_test_dispatch_handler",
        })

        vehicle = self._create_vehicle()
        driver = self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()

        self.assertEqual(len(calls), 1)
        event_name, payload = calls[0]
        self.assertEqual(event_name, "deployfleet.dispatch.assigned")
        self.assertEqual(payload["driver_id"], driver.id)
        self.assertEqual(payload["vehicle_id"], vehicle.id)

    def test_confirming_an_already_confirmed_assignment_raises(self):
        """Regression test for an engineering-audit finding:
        action_confirm() had no state guard at all - a double-click (or
        a client retry) could re-confirm an already-confirmed assignment
        with no error."""
        self._create_vehicle()
        self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_confirm()
        with self.assertRaises(UserError):
            assignment.action_confirm()

    def test_confirming_a_vehicle_already_committed_elsewhere_raises(self):
        """Regression test: nothing previously stopped two different
        shipments each having a proposed assignment against the SAME
        vehicle, and confirming both - the second confirm silently
        overwrote the vehicle's status a second time with no error,
        double-booking it. Deliberately not override-able (unlike the
        higher-scored-candidate check): a vehicle genuinely can't be in
        two places, so an override wouldn't resolve the conflict, just
        paper over it."""
        vehicle = self._create_vehicle()
        self._create_driver(name="Driver A")
        self._create_driver(name="Driver B")
        shipment_one = self._create_shipment()
        shipment_two = self._create_shipment()
        [assignment_one] = shipment_one.action_suggest_assignments(limit=1)
        # Both shipments proposed against the same (only) vehicle.
        [assignment_two] = shipment_two.action_suggest_assignments(limit=1)
        self.assertEqual(assignment_one.vehicle_id, vehicle)
        self.assertEqual(assignment_two.vehicle_id, vehicle)

        assignment_one.action_confirm()
        with self.assertRaises(UserError):
            assignment_two.action_confirm()
        self.assertEqual(assignment_two.state, "proposed")

    def test_cancelling_an_already_cancelled_assignment_raises(self):
        self._create_vehicle()
        self._create_driver()
        shipment = self._create_shipment()
        [assignment] = shipment.action_suggest_assignments(limit=1)
        assignment.action_cancel()
        with self.assertRaises(UserError):
            assignment.action_cancel()
