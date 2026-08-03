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
