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

    def test_dispatch_board_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_dispatch_board")
        self.assertEqual(action.tag, "deployfleet_ui.dispatch_board")

    def test_dispatch_board_menu_is_second_in_deployfleet_root(self):
        mission_control_menu = self.env.ref("deployfleet_ui.menu_deployfleet_mission_control")
        dispatch_board_menu = self.env.ref("deployfleet_ui.menu_deployfleet_dispatch_board")
        self.assertEqual(dispatch_board_menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))
        siblings = self.env["ir.ui.menu"].search(
            [("parent_id", "=", dispatch_board_menu.parent_id.id)], order="sequence"
        )
        self.assertEqual(list(siblings[:2]), [mission_control_menu, dispatch_board_menu])

    def test_fleet_command_center_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_fleet_command_center")
        self.assertEqual(action.tag, "deployfleet_ui.fleet_command_center")

    def test_fleet_command_center_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_fleet_command_center")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_copilot_console_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_copilot_console")
        self.assertEqual(action.tag, "deployfleet_ui.copilot_console")

    def test_copilot_console_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_copilot_console")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_driver_scorecards_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_driver_scorecards")
        self.assertEqual(action.tag, "deployfleet_ui.driver_scorecards")

    def test_driver_scorecards_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_driver_scorecards")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_workshop_board_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_workshop_board")
        self.assertEqual(action.tag, "deployfleet_ui.workshop_board")

    def test_workshop_board_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_workshop_board")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_parts_registry_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_parts_registry")
        self.assertEqual(action.tag, "deployfleet_ui.parts_registry")

    def test_parts_registry_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_parts_registry")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_asset_registry_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_asset_registry")
        self.assertEqual(action.tag, "deployfleet_ui.asset_registry")

    def test_asset_registry_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_asset_registry")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_vehicle_types_workspace_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_vehicle_types_workspace")
        self.assertEqual(action.tag, "deployfleet_ui.vehicle_types_workspace")

    def test_vehicle_types_workspace_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_vehicle_types_workspace")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_fuel_intelligence_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_fuel_intelligence")
        self.assertEqual(action.tag, "deployfleet_ui.fuel_intelligence")

    def test_fuel_intelligence_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_fuel_intelligence")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_tyre_manager_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_tyre_manager")
        self.assertEqual(action.tag, "deployfleet_ui.tyre_manager")

    def test_tyre_manager_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_tyre_manager")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_insurance_center_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_insurance_center")
        self.assertEqual(action.tag, "deployfleet_ui.insurance_center")

    def test_insurance_center_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_insurance_center")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_maintenance_planner_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_maintenance_planner")
        self.assertEqual(action.tag, "deployfleet_ui.maintenance_planner")

    def test_maintenance_planner_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_maintenance_planner")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))
