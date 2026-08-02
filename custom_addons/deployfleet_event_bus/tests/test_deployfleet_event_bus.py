import json

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetEventBus(TransactionCase):
    def _register_test_handler(self, model_name="res.partner", method_name="_test_handle_bus_event"):
        """Monkeypatches a throwaway handler method onto an already-installed
        model so the registry pattern can be exercised without needing a
        dedicated test model. Cleaned up automatically after the test."""
        model_class = type(self.env[model_name])
        calls = []

        def _handler(_self, event_name, source_model, source_id, payload):
            calls.append((event_name, source_model, source_id, payload))

        setattr(model_class, method_name, _handler)
        self.addCleanup(delattr, model_class, method_name)
        return calls

    def test_dispatch_calls_matching_subscriber(self):
        calls = self._register_test_handler()
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "vehicle.breakdown.*",
            "model_name": "res.partner",
            "method_name": "_test_handle_bus_event",
        })

        log = self.env["deployfleet.event.log"].register_event(
            "vehicle.breakdown.created", "res.partner", self.env.user.partner_id.id, {"foo": "bar"}
        )

        self.assertEqual(log.state, "processed")
        self.assertEqual(len(calls), 1)
        event_name, source_model, _source_id, payload = calls[0]
        self.assertEqual(event_name, "vehicle.breakdown.created")
        self.assertEqual(source_model, "res.partner")
        self.assertEqual(payload, {"foo": "bar"})

    def test_non_matching_pattern_is_not_called(self):
        calls = self._register_test_handler()
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "compliance.*",
            "model_name": "res.partner",
            "method_name": "_test_handle_bus_event",
        })

        log = self.env["deployfleet.event.log"].register_event(
            "vehicle.breakdown.created", "res.partner", 1
        )

        self.assertEqual(log.state, "processed")
        self.assertEqual(calls, [])

    def test_inactive_subscription_is_not_called(self):
        calls = self._register_test_handler()
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "vehicle.*",
            "model_name": "res.partner",
            "method_name": "_test_handle_bus_event",
            "active": False,
        })

        self.env["deployfleet.event.log"].register_event("vehicle.breakdown.created", "res.partner", 1)
        self.assertEqual(calls, [])

    def test_subscriber_exception_marks_event_failed_but_does_not_raise(self):
        model_class = type(self.env["res.partner"])

        def _raising_handler(_self, event_name, source_model, source_id, payload):
            raise ValueError("boom")

        setattr(model_class, "_test_raising_handler", _raising_handler)
        self.addCleanup(delattr, model_class, "_test_raising_handler")

        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "vehicle.*",
            "model_name": "res.partner",
            "method_name": "_test_raising_handler",
        })

        log = self.env["deployfleet.event.log"].register_event("vehicle.breakdown.created", "res.partner", 1)

        self.assertEqual(log.state, "failed")
        self.assertIn("boom", log.error_message)

    def test_payload_round_trips_through_json(self):
        log = self.env["deployfleet.event.log"].register_event(
            "trip.delayed", "res.partner", 1, {"minutes_late": 45, "reason": "traffic"}
        )
        self.assertEqual(json.loads(log.event_data), {"minutes_late": 45, "reason": "traffic"})

    def test_core_module_has_no_knowledge_of_specific_subscribers(self):
        """Guards against reintroducing the hardcoded if-chain this module
        replaces (risk #4): dispatch must work for a subscriber the bus has
        never heard of, registered purely as data."""
        calls = self._register_test_handler(method_name="_test_handle_bus_event")
        sub = self.env["deployfleet.event.subscription"].create({
            "event_pattern": "anything.*",
            "model_name": "res.partner",
            "method_name": "_test_handle_bus_event",
        })
        self.assertTrue(sub.exists())
        self.env["deployfleet.event.log"].register_event("anything.happened", "res.partner", 1)
        self.assertEqual(len(calls), 1)
