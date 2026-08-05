/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { helpContextStore } from "./help_context";

const QUICK_LINKS = [
    { key: "getting-started", label: "Getting Started", icon: "fa fa-compass", actionXmlId: "deployfleet_ui.action_deployfleet_help_center_getting_started" },
    { key: "faq", label: "FAQ", icon: "fa fa-question-circle", actionXmlId: "deployfleet_ui.action_deployfleet_help_center_faq" },
    { key: "troubleshooting", label: "Troubleshooting", icon: "fa fa-life-ring", actionXmlId: "deployfleet_ui.action_deployfleet_help_center_troubleshooting" },
];

/**
 * The persistent Help Trigger (doc 22 §4) — a small, always-mounted
 * corner button present across every workspace, structurally the same
 * pattern as the Launcher's own persistent corner trigger and the
 * Copilot Rail's docked tab: `main_components` mount, `state.open`,
 * scrim + slide-out panel, a global hotkey (`Alt+K`, free - h/d/f/c/b/r/
 * i/l/a are already claimed by Mission Control, the six Mega Menu
 * domains, the Launcher, and the Copilot Rail).
 *
 * Positioned bottom-left (the Launcher trigger owns bottom-right, the
 * Copilot Rail owns the vertically-centered right edge - this is the one
 * remaining uncontested corner).
 *
 * Reads `helpContextStore` (doc 22 §4's ambient tier-1 mechanism,
 * `./help_context.js`) via `useState()` to register as a subscriber, the
 * same pattern the Copilot Rail already uses for its own context store.
 * When a workspace has opted in via `useHelpContext().setContext(...)`,
 * the panel's top link opens the Help Center scoped to that workspace's
 * topic instead of just the plain home landing page.
 */
export class DeployfleetHelpTrigger extends Component {
    static template = "deployfleet_ui.HelpTrigger";
    static props = {};

    setup() {
        this.actionService = useService("action");
        this.helpContext = useState(helpContextStore);
        this.quickLinks = QUICK_LINKS;
        this.state = useState({ open: false });

        useHotkey("alt+k", () => this.toggleOpen(), { global: true, allowRepeat: false });
        useHotkey(
            "escape",
            () => {
                if (this.state.open) {
                    this.close();
                }
            },
            { global: true, allowRepeat: false },
        );
    }

    toggleOpen() {
        this.state.open = !this.state.open;
    }

    close() {
        this.state.open = false;
    }

    onOpenHome() {
        this.actionService.doAction("deployfleet_ui.action_deployfleet_help_center", { clearBreadcrumbs: true });
        this.close();
    }

    onOpenContextual() {
        // A dynamic, per-workspace context key - not one of the fixed,
        // pre-registered Mega Menu tile actions, so an inline action
        // descriptor is the right tool here, the same considered
        // decision already made for the Command Palette's Help results
        // (see deployfleet_command_provider.js's docstring on this).
        this.actionService.doAction(
            {
                type: "ir.actions.client",
                tag: "deployfleet_ui.help_center",
                params: { context_key: this.helpContext.contextKey },
            },
            { clearBreadcrumbs: true },
        );
        this.close();
    }

    onQuickLinkClick(link) {
        this.actionService.doAction(link.actionXmlId, { clearBreadcrumbs: true });
        this.close();
    }
}

registry.category("main_components").add("deployfleet_ui.HelpTrigger", {
    Component: DeployfleetHelpTrigger,
});
