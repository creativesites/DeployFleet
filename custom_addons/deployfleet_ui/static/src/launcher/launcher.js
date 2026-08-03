/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { DEPLOYFLEET_MEGA_MENU_DOMAINS } from "../mega_menu/domain_content";

// Mission Control (Phase C / Slice 1) reclaims the Alt+H shortcut doc 16
// §5 always intended for "Home" — it was left unused in Phase B/Slice 3
// specifically so this didn't need a remap once Mission Control shipped.
// Unlike the six Mega Menu domains below, its label/subtitle aren't
// pulled from domain_content.js since it isn't one of those domains.
const HOME_DESTINATION = {
    key: "home",
    actionXmlId: "deployfleet_ui.action_deployfleet_mission_control",
    icon: "fa fa-home",
    colorFamily: "home",
    shortcut: "h",
    label: "Mission Control",
    subtitle: "Today's fleet at a glance — attention strip, KPIs, and quick links.",
};

const MEGA_MENU_DESTINATIONS = [
    {
        key: "dispatch",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_dispatch",
        icon: "fa fa-th-large",
        colorFamily: "dispatch",
        shortcut: "d",
    },
    {
        key: "fleet",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_fleet",
        icon: "fa fa-truck",
        colorFamily: "fleet",
        shortcut: "f",
    },
    {
        key: "compliance",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_compliance",
        icon: "fa fa-shield",
        colorFamily: "compliance",
        shortcut: "c",
    },
    {
        key: "billing",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_billing",
        icon: "fa fa-money",
        colorFamily: "billing",
        shortcut: "b",
    },
    {
        key: "driver",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_driver",
        icon: "fa fa-id-badge",
        colorFamily: "driver",
        shortcut: "r",
    },
    {
        key: "ai",
        actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_ai",
        icon: "fa fa-magic",
        colorFamily: "ai",
        shortcut: "i",
    },
].map((entry) => ({
    ...entry,
    label: DEPLOYFLEET_MEGA_MENU_DOMAINS[entry.key].label,
    subtitle: DEPLOYFLEET_MEGA_MENU_DOMAINS[entry.key].subtitle,
}));

const DOMAIN_DESTINATIONS = [HOME_DESTINATION, ...MEGA_MENU_DESTINATIONS];

const RECENTS_STORAGE_KEY = "deployfleet_ui.launcher.recents";
const FAVORITES_STORAGE_KEY = "deployfleet_ui.launcher.favorites";
const MAX_RECENTS = 6;

function readStoredList(key) {
    try {
        const raw = window.localStorage.getItem(key);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function writeStoredList(key, list) {
    try {
        window.localStorage.setItem(key, JSON.stringify(list));
    } catch {
        // Private-browsing/storage-disabled contexts: recents/favorites
        // simply don't persist across sessions - never let that break
        // the launcher itself.
    }
}

/**
 * The DeployFleet Launcher (doc 16 §3.2/§5, Phase B Slice 3) — a
 * full-screen Command-Layer overlay with a priority-workspace strip
 * (Alt+<letter> shortcuts straight to each domain), recents/favorites
 * persisted client-side, and a grid of destinations.
 *
 * Scope note, a deliberate risk decision: doc 16 describes this pattern
 * as replacing Odoo's native app-switcher grid by patching `web.NavBar`'s
 * apps-menu button. This slice does NOT do that — a bad xpath match
 * against this exact Odoo 19 nightly's NavBar template could break the
 * top navigation bar across the *entire product*, not just this
 * feature, and that template's current internal structure cannot be
 * verified against a live instance from this development environment.
 * Instead, the Launcher is a self-contained, always-mounted overlay
 * (global hotkey + a persistent corner button), delivering every other
 * part of the spec — glass, priority strip, keyboard shortcuts,
 * destination grid, recents/favorites — without touching Odoo's own
 * chrome at all. Patching the native apps-button to open this same
 * overlay remains a valid future enhancement once it can be verified
 * against a live instance first, not something to attempt speculatively
 * against production chrome.
 *
 * A second, related scope note: DeployFleet nests all 43 modules under
 * one single "DeployFleet" app menu (`deployfleet_core.menu_deployfleet_
 * root`) rather than many distinct top-level Odoo apps the way
 * DeployGuard did — so a grid populated purely from Odoo's own
 * `getApps()` would be nearly empty. The Launcher's destination grid is
 * populated from the six curated Mega Menu domains instead (genuinely
 * the meaningful "workspaces" today), with Odoo's own real top-level
 * apps (Settings, Discuss, ...) shown separately below as "Other Apps."
 */
export class DeployfleetLauncher extends Component {
    static template = "deployfleet_ui.Launcher";
    static props = {};

    setup() {
        this.menuService = useService("menu");
        this.actionService = useService("action");
        this.state = useState({
            open: false,
            searchQuery: "",
            recents: readStoredList(RECENTS_STORAGE_KEY),
            favorites: readStoredList(FAVORITES_STORAGE_KEY),
        });

        useHotkey("alt+l", () => this.toggleOpen(), { global: true, allowRepeat: false });
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

    get domains() {
        return DOMAIN_DESTINATIONS;
    }

    get otherApps() {
        return this.menuService.getApps().filter((app) => app.name !== "DeployFleet");
    }

    get filteredDomains() {
        return this.filterByQuery(this.domains, (item) => `${item.label} ${item.subtitle}`);
    }

    get filteredApps() {
        return this.filterByQuery(this.otherApps, (item) => item.name);
    }

    filterByQuery(list, textOf) {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) {
            return list;
        }
        return list.filter((item) => textOf(item).toLowerCase().includes(query));
    }

    isFavorite(key) {
        return this.state.favorites.some((entry) => entry.key === key);
    }

    toggleOpen() {
        if (this.state.open) {
            this.close();
        } else {
            this.state.open = true;
            this.state.searchQuery = "";
        }
    }

    close() {
        this.state.open = false;
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    recordRecent(key, label, icon) {
        const withoutExisting = this.state.recents.filter((entry) => entry.key !== key);
        const updated = [{ key, label, icon }, ...withoutExisting].slice(0, MAX_RECENTS);
        this.state.recents = updated;
        writeStoredList(RECENTS_STORAGE_KEY, updated);
    }

    toggleFavorite(ev, key, label, icon) {
        ev.stopPropagation();
        const isFav = this.isFavorite(key);
        const updated = isFav
            ? this.state.favorites.filter((entry) => entry.key !== key)
            : [...this.state.favorites, { key, label, icon }];
        this.state.favorites = updated;
        writeStoredList(FAVORITES_STORAGE_KEY, updated);
    }

    onDomainClick(domain) {
        this.recordRecent(domain.key, domain.label, domain.icon);
        this.actionService.doAction(domain.actionXmlId, { clearBreadcrumbs: true });
        this.close();
    }

    onAppClick(app) {
        this.recordRecent(`app-${app.id}`, app.name, "fa fa-th");
        this.menuService.selectMenu(app);
        this.close();
    }

    onSavedItemClick(item) {
        const domain = this.domains.find((entry) => entry.key === item.key);
        if (domain) {
            this.onDomainClick(domain);
            return;
        }
        const app = this.otherApps.find((entry) => `app-${entry.id}` === item.key);
        if (app) {
            this.onAppClick(app);
        }
    }
}

registry.category("main_components").add("deployfleet_ui.Launcher", {
    Component: DeployfleetLauncher,
});
