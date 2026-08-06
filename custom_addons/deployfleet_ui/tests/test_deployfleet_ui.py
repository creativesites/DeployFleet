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

    def test_deployfleet_root_menu_opens_mission_control(self):
        # Odoo's web client picks the post-login landing screen by
        # selecting the first root-level app menu (by sequence) and
        # running its own action directly - a root menu with no action
        # of its own does nothing at all (verified against the real
        # menu_service.js source). Without this, the sequence fix alone
        # would land on a blank screen instead of Mission Control.
        root_menu = self.env.ref("deployfleet_core.menu_deployfleet_root")
        mission_control_action = self.env.ref("deployfleet_ui.action_deployfleet_mission_control")
        self.assertEqual(root_menu.action, f"ir.actions.client,{mission_control_action.id}")

    def test_deployfleet_root_menu_beats_discuss_sequence(self):
        # Found live (Aug 2026): every user landed on Discuss/OdooBot's
        # welcome message after login, since DeployFleet's own root menu
        # (sequence 20) lost the "first root app" race to Discuss's
        # (mail.menu_root_discuss, sequence 5 in real Odoo core). This
        # pins the fix directly against Discuss's actual menu, not just
        # an arbitrary low number, so a future change to either side
        # that reintroduces the regression fails loudly here.
        root_menu = self.env.ref("deployfleet_core.menu_deployfleet_root")
        discuss_menu = self.env.ref("mail.menu_root_discuss")
        self.assertLess(root_menu.sequence, discuss_menu.sequence)

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

    def test_driver_advances_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_driver_advances")
        self.assertEqual(action.tag, "deployfleet_ui.driver_advances")

    def test_driver_advances_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_driver_advances")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_leave_planner_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_leave_planner")
        self.assertEqual(action.tag, "deployfleet_ui.leave_planner")

    def test_leave_planner_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_leave_planner")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_payroll_center_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_payroll_center")
        self.assertEqual(action.tag, "deployfleet_ui.payroll_center")

    def test_payroll_center_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_payroll_center")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_trip_board_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_trip_board")
        self.assertEqual(action.tag, "deployfleet_ui.trip_board")

    def test_trip_board_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_trip_board")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_delivery_center_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_delivery_center")
        self.assertEqual(action.tag, "deployfleet_ui.delivery_center")

    def test_delivery_center_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_delivery_center")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_route_manager_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_route_manager")
        self.assertEqual(action.tag, "deployfleet_ui.route_manager")

    def test_route_manager_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_route_manager")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_depot_registry_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_depot_registry")
        self.assertEqual(action.tag, "deployfleet_ui.depot_registry")

    def test_depot_registry_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_depot_registry")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_ai_predictions_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_ai_predictions")
        self.assertEqual(action.tag, "deployfleet_ui.ai_predictions")

    def test_ai_predictions_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_ai_predictions")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))

    def test_ai_action_history_action_registered(self):
        action = self.env.ref("deployfleet_ui.action_deployfleet_ai_action_history")
        self.assertEqual(action.tag, "deployfleet_ui.ai_action_history")

    def test_ai_action_history_menu_parented_to_deployfleet_root(self):
        menu = self.env.ref("deployfleet_ui.menu_deployfleet_ai_action_history")
        self.assertEqual(menu.parent_id, self.env.ref("deployfleet_core.menu_deployfleet_root"))
