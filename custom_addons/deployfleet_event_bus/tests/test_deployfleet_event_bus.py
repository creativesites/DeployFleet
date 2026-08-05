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

    def test_register_event_works_for_a_real_dispatcher_user(self):
        # Regression test for the engineering-audit finding: this
        # model's ACL grants create/write to base.group_system only,
        # and no DeployFleet role implies it. register_event()'s
        # self.create() and _dispatch_event()'s self.write() were
        # unsudo'd, so every real call site (dispatch confirm/cancel,
        # trip lifecycle, delivery creation, vehicle status changes,
        # invoice creation, maintenance recording) would raise
        # AccessError the moment a real dispatcher account touched it —
        # the same bug shape already found and fixed once for the AI
        # pipeline. Exercised end to end as a real dispatcher-group
        # user, the way the AI pipeline's own regression test does,
        # rather than just as the TransactionCase superuser.
        calls = self._register_test_handler(method_name="_test_handle_bus_event_as_caller")
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "vehicle.*",
            "model_name": "res.partner",
            "method_name": "_test_handle_bus_event_as_caller",
        })
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Event Bus Dispatcher User", "login": "event_bus_dispatcher_user@example.com",
            "email": "event_bus_dispatcher_user@example.com", "group_ids": [(6, 0, [dispatcher_group.id])],
        })

        log = self.env["deployfleet.event.log"].with_user(dispatcher_user).register_event(
            "vehicle.breakdown.created", "res.partner", self.env.user.partner_id.id,
        )

        self.assertEqual(log.state, "processed")
        self.assertEqual(len(calls), 1)

    def test_dispatch_still_runs_as_the_calling_user_not_sudo(self):
        # The sudo() fix above is deliberately scoped to just the
        # event-log bookkeeping (create/state write) — subscriber
        # handlers must keep seeing the real calling user, since
        # existing subscribers (e.g. the AI entity-summary cache
        # invalidation) already apply their own sudo() only where they
        # specifically need to, and a blanket-sudo'd dispatch would
        # silently change that.
        model_class = type(self.env["res.partner"])
        seen_uids = []

        def _handler(_self, event_name, source_model, source_id, payload):
            seen_uids.append(_self.env.uid)

        setattr(model_class, "_test_uid_handler", _handler)
        self.addCleanup(delattr, model_class, "_test_uid_handler")
        self.env["deployfleet.event.subscription"].create({
            "event_pattern": "vehicle.*",
            "model_name": "res.partner",
            "method_name": "_test_uid_handler",
        })
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Event Bus UID Dispatcher User", "login": "event_bus_uid_dispatcher_user@example.com",
            "email": "event_bus_uid_dispatcher_user@example.com", "group_ids": [(6, 0, [dispatcher_group.id])],
        })

        self.env["deployfleet.event.log"].with_user(dispatcher_user).register_event(
            "vehicle.breakdown.created", "res.partner", 1,
        )

        self.assertEqual(seen_uids, [dispatcher_user.id])

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
