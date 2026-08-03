from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetUi(TransactionCase):
    """This module ships no models - it is a frontend asset/component
    library - so these tests only confirm the one backend-visible piece
    (the debug-only Component Showcase action/menu) is wired correctly.
    Actual OWL component rendering is not covered by this repository's
    CI (no headless-browser test step exists yet); see README.rst."""

    def test_showcase_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_ui_component_showcase")
        self.assertEqual(action.tag, "deployfleet_ui.component_showcase")

    def test_showcase_menu_points_to_showcase_action(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_ui_component_showcase")
        action = self.env.ref("deployfleet_ui.action_deployfleet_ui_component_showcase")
        self.assertEqual(menu.action, f"ir.actions.client,{action.id}")

    def test_mega_menu_actions_registered(self):
        for xmlid in (
            "action_deployfleet_mega_menu_fleet",
            "action_deployfleet_mega_menu_dispatch",
            "action_deployfleet_mega_menu_compliance",
            "action_deployfleet_mega_menu_billing",
            "action_deployfleet_mega_menu_driver",
            "action_deployfleet_mega_menu_ai",
        ):
            action = self.env.ref(f"deployfleet_ui.{xmlid}")
            self.assertEqual(action.tag, "deployfleet_ui.domain_mega_menu")

    def test_mission_control_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_mission_control")
        self.assertEqual(action.tag, "deployfleet_ui.mission_control")

    def test_mission_control_menu_is_first_in_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_mission_control")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))
        siblings = self.env["ir.ui.menu"].search([("parent_id", "=", menu.parent_id.id)], order="sequence")
        self.assertEqual(siblings[0], menu)
