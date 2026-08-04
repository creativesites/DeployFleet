from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAIEntitySummary(TransactionCase):
    """Regression tests for the entity-summary cache (doc 21 §6 -
    docs/architecture/21-copilot-rail-architecture.md)."""

    def test_upsert_creates_then_updates_in_place(self):
        model = self.env["deployfleet.ai.entity.summary"]
        created = model.upsert("deployfleet.vehicle", 999001, "first summary", "sig-1")
        self.assertEqual(model.search_count([("res_model", "=", "deployfleet.vehicle"), ("res_id", "=", 999001)]), 1)

        updated = model.upsert("deployfleet.vehicle", 999001, "second summary", "sig-2")
        self.assertEqual(created.id, updated.id, "upsert() must write the existing row, not create a second one")
        self.assertEqual(updated.summary_text, "second summary")
        self.assertEqual(updated.source_signature, "sig-2")
        self.assertEqual(model.search_count([("res_model", "=", "deployfleet.vehicle"), ("res_id", "=", 999001)]), 1)

    def test_get_cached_returns_empty_recordset_when_absent(self):
        model = self.env["deployfleet.ai.entity.summary"]
        result = model.get_cached("deployfleet.vehicle", 999002)
        self.assertFalse(result)

    def test_handle_bus_event_deletes_matching_vehicle_summary(self):
        model = self.env["deployfleet.ai.entity.summary"]
        model.upsert("deployfleet.vehicle", 999003, "stale summary", "sig-stale")
        model._handle_bus_event(
            "deployfleet.trip.completed", "deployfleet.trip", 1, {"vehicle_id": 999003},
        )
        self.assertFalse(model.get_cached("deployfleet.vehicle", 999003))

    def test_handle_bus_event_ignores_payload_without_vehicle_id(self):
        model = self.env["deployfleet.ai.entity.summary"]
        model.upsert("deployfleet.vehicle", 999004, "still here", "sig-x")
        model._handle_bus_event("deployfleet.trip.completed", "deployfleet.trip", 1, {})
        self.assertTrue(model.get_cached("deployfleet.vehicle", 999004))

    def test_handle_bus_event_works_for_a_non_system_user(self):
        """The event bus dispatcher invokes every subscriber's handler
        using the *publisher's* env unchanged - a dispatcher confirming
        an assignment is not base.group_system, so this handler must
        sudo() internally or it would raise AccessError on every real
        trip-completed/dispatch-assigned event."""
        dispatcher_group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
        dispatcher_user = self.env["res.users"].create({
            "name": "Entity Summary Dispatcher", "login": "entity_summary_dispatcher@example.com",
            "email": "entity_summary_dispatcher@example.com",
            "group_ids": [(6, 0, [dispatcher_group.id])],
        })
        model = self.env["deployfleet.ai.entity.summary"]
        model.upsert("deployfleet.vehicle", 999005, "will be cleared", "sig-y")
        model.with_user(dispatcher_user)._handle_bus_event(
            "deployfleet.dispatch.assigned", "deployfleet.dispatch.assignment", 1, {"vehicle_id": 999005},
        )
        self.assertFalse(model.get_cached("deployfleet.vehicle", 999005))

    def test_real_event_bus_dispatch_invalidates_cache(self):
        """End-to-end through the real deployfleet.event.log.register_event()
        entry point, not just a direct handler call - confirms the
        subscription records (data/deployfleet_ai_entity_summary_event_
        subscriptions.xml) are actually wired up."""
        model = self.env["deployfleet.ai.entity.summary"]
        model.upsert("deployfleet.vehicle", 999006, "about to go stale", "sig-z")
        self.env["deployfleet.event.log"].register_event(
            "deployfleet.trip.completed", "deployfleet.trip", 1, {"vehicle_id": 999006},
        )
        self.assertFalse(model.get_cached("deployfleet.vehicle", 999006))


@tagged("post_install", "-at_install")
class TestDeployfleetAICompanyProfile(TransactionCase):
    def test_write_bumps_updated_date(self):
        profile = self.env["deployfleet.ai.company.profile"].create({
            "company_id": self.env.company.id, "profile_text": "Initial notes.",
        })
        first_updated = profile.updated_date
        profile.write({"profile_text": "Revised notes."})
        self.assertGreaterEqual(profile.updated_date, first_updated)

    def test_only_one_profile_per_company(self):
        self.env["deployfleet.ai.company.profile"].create({"company_id": self.env.company.id})
        with self.assertRaises(Exception):  # noqa: B017 — SQL unique-constraint IntegrityError
            self.env["deployfleet.ai.company.profile"].create({"company_id": self.env.company.id})


@tagged("post_install", "-at_install")
class TestDeployfleetAIChatSessionCompanyProfile(TransactionCase):
    """Regression tests for _effective_system_prompt() folding the
    company profile into Chat (doc 21 §6)."""

    def _create_session(self):
        feature = self.env["deployfleet.ai.feature"].create({
            "key": "entity_summary_test_feature", "name": "Entity Summary Test Feature",
            "enabled": True, "model_tier": "cheap", "data_category": "general",
        })
        return self.env["deployfleet.ai.chat.session"].create({
            "name": "Test Chat", "feature_id": feature.id, "system_prompt": "You are a helpful agent.",
        })

    def test_no_profile_returns_plain_system_prompt(self):
        session = self._create_session()
        self.assertEqual(session._effective_system_prompt(), "You are a helpful agent.")

    def test_profile_text_is_prepended(self):
        self.env["deployfleet.ai.company.profile"].create({
            "company_id": self.env.company.id, "profile_text": "12 trucks, operates in Lusaka and Ndola.",
        })
        session = self._create_session()
        effective = session._effective_system_prompt()
        self.assertIn("12 trucks, operates in Lusaka and Ndola.", effective)
        self.assertIn("You are a helpful agent.", effective)

    def test_empty_profile_text_does_not_change_prompt(self):
        self.env["deployfleet.ai.company.profile"].create({
            "company_id": self.env.company.id, "profile_text": False,
        })
        session = self._create_session()
        self.assertEqual(session._effective_system_prompt(), "You are a helpful agent.")
