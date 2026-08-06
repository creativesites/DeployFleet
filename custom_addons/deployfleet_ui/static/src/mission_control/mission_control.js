/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";
import { DEPLOYFLEET_MEGA_MENU_DOMAINS } from "../mega_menu/domain_content";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

const SESSION_STORAGE_KEY = "deployfleet_demo_welcome_dismissed";

// Demo-only welcome card content (doc 22 follow-up, Aug 2026) - shown
// instead of the First-Time Setup strip above, never alongside it, since
// that strip's copy ("Add your first vehicle", "Create your first
// shipment") is written for a real customer setting up their own
// company and would actively confuse a demo visitor browsing pre-seeded
// data. Detected purely client-side from the login string
// deployfleet_demo_zm's own controller creates (demo.<role>@deployfleet.
// demo) - no new backend field/RPC needed. Deliberately excludes
// "customer": that persona is a portal user (base.group_portal), which
// never lands on Mission Control at all - it gets Odoo's separate portal
// UI, a genuinely different surface this card can't reach.
//
// Quick-link destinations were chosen only after checking each role's
// actual ACLs, not assumed: group_deployfleet_driver has read access to
// deployfleet.trip/.shipment/.vehicle but NOT deployfleet.driver.
// performance.event (dispatcher/manager-only, a real pre-existing gap
// flagged separately, not fixed here) - so Driver's own links stay to
// Trip Board and Help Center rather than Driver Scorecards, which would
// 403 on the very screen this card recommends.
const DEMO_ROLE_CONTENT = {
    owner: {
        heading: "You're exploring DeployFleet as Owner / Manager",
        pitch: "Full visibility — every workspace, every domain, no restrictions.",
        bullets: [
            "The attention strip and KPIs below update live from real demo data.",
            "You can reach every domain — Dispatch, Fleet, Compliance, Billing, AI.",
            "Ask the Copilot a question about the fleet — it's a real, working assistant.",
        ],
        links: [
            { actionXmlId: "deployfleet_ui.action_deployfleet_dispatch_board", label: "Dispatch Board", icon: "fa fa-th-large" },
            { actionXmlId: "deployfleet_ui.action_deployfleet_fleet_command_center", label: "Fleet Command Center", icon: "fa fa-truck" },
            { actionXmlId: "deployfleet_ui.action_deployfleet_copilot_console", label: "Copilot Console", icon: "fa fa-magic" },
        ],
    },
    dispatcher: {
        heading: "You're exploring DeployFleet as a Dispatcher",
        pitch: "This is where live operations get run — day in, day out.",
        bullets: [
            "The Dispatch Board is your main workspace: confirm shipments, assign drivers and vehicles.",
            "Track every vehicle's status and trips from the Fleet Command Center.",
            "Compliance issues that could block a dispatch show up automatically.",
        ],
        links: [
            { actionXmlId: "deployfleet_ui.action_deployfleet_dispatch_board", label: "Dispatch Board", icon: "fa fa-th-large" },
            { actionXmlId: "deployfleet_ui.action_deployfleet_trip_board", label: "Trip Board", icon: "fa fa-road" },
            { actionXmlId: "deployfleet_ui.action_deployfleet_fleet_command_center", label: "Fleet Command Center", icon: "fa fa-truck" },
        ],
    },
    driver: {
        heading: "You're exploring DeployFleet as a Driver",
        pitch: "The road-facing side of the product — what a driver sees day to day.",
        bullets: [
            "The Trip Board shows assigned trips, in the same real data every other role sees.",
            "This demo shows the backend web view — the real driver experience is a dedicated mobile app.",
            "Need a hand? The Help Center (bottom-left corner) has plain-language guides.",
        ],
        links: [
            { actionXmlId: "deployfleet_ui.action_deployfleet_trip_board", label: "Trip Board", icon: "fa fa-road" },
            { actionXmlId: "deployfleet_ui.action_deployfleet_help_center", label: "Help Center", icon: "fa fa-question-circle" },
        ],
    },
};

function getDemoRole() {
    const match = /^demo\.([a-z]+)@deployfleet\.demo$/.exec(user.login || "");
    return match ? match[1] : null;
}

// Every domain here is the underlying record set doc 16 §3.3 calls for
// ("each count a clickable pill jumping straight to the underlying
// list"), not the Mega Menu that contains it — verified directly against
// each model's source before writing these: deployfleet.shipment.state
// ("confirmed" = ready for dispatch, not yet assigned),
// deployfleet.compliance.document.state ("expiring_soon"/"expired" are
// the model's own computed classification, not re-derived here),
// deployfleet.vehicle.status ("breakdown"), deployfleet.ai.action.
// request.state ("pending_approval"). The two document-expiry pills'
// destination was repointed from the stock document list to the new
// Compliance Center wall (Compliance domain build) — the same
// stale-tile fix already applied to the Dispatch Board/AI Predictions
// pills in earlier domains; the counts themselves are unchanged.
const ATTENTION_ITEMS = [
    {
        stateKey: "unassignedShipments",
        label: "Unassigned shipments",
        status: "danger",
        actionXmlId: "deployfleet_ui.action_deployfleet_dispatch_board",
    },
    {
        stateKey: "expiredDocuments",
        label: "Expired documents",
        status: "danger",
        actionXmlId: "deployfleet_ui.action_deployfleet_compliance_center",
    },
    {
        stateKey: "breakdownVehicles",
        label: "Vehicles in breakdown",
        status: "danger",
        actionXmlId: "deployfleet_vehicle.action_deployfleet_vehicle",
    },
    {
        stateKey: "expiringDocuments",
        label: "Documents expiring soon",
        status: "warning",
        actionXmlId: "deployfleet_ui.action_deployfleet_compliance_center",
    },
    {
        // The "ai" StatusPill variant is a deliberate, correct use of
        // doc 17 §2.3's reserved AI-content violet — this pill is
        // literally about AI-suggested actions awaiting human review.
        stateKey: "pendingApprovals",
        label: "Pending AI approvals",
        status: "ai",
        actionXmlId: "deployfleet_ai_actions.action_deployfleet_ai_action_request",
    },
];

const DOMAIN_QUICK_LINKS = [
    { key: "dispatch", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_dispatch", icon: "fa fa-th-large" },
    { key: "fleet", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_fleet", icon: "fa fa-truck" },
    { key: "compliance", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_compliance", icon: "fa fa-shield" },
    { key: "billing", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_billing", icon: "fa fa-money" },
    { key: "driver", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_driver", icon: "fa fa-id-badge" },
    { key: "ai", actionXmlId: "deployfleet_ui.action_deployfleet_mega_menu_ai", icon: "fa fa-magic" },
].map((entry) => ({ ...entry, label: DEPLOYFLEET_MEGA_MENU_DOMAINS[entry.key].label }));

/**
 * Mission Control (doc 16 §5/§7.2, Phase C / Slice 1) — the owner/manager
 * Home Dashboard. Answers doc 16 §2.4's question directly: "is anything
 * wrong today?" A silent-unless-nonzero attention strip (doc 16 §3.3 —
 * the single most operationally valuable idea found in the DeployGuard
 * audit) computed from real parallel `searchCount` calls, three real
 * KPIs, and quick links to the six Mega Menu domains.
 *
 * Every count and sum here is a genuine ORM query against real
 * DeployFleet models — not placeholder numbers. Deliberately no hard
 * manifest dependency on deployfleet_dispatch/deployfleet_compliance/
 * deployfleet_vehicle/deployfleet_ai_actions/deployfleet_billing: these
 * model names are referenced as plain strings resolved at runtime, the
 * same soft-coupling decision already made for the Mega Menu tiles and
 * Command Palette record search (all 43 modules are always installed
 * together in practice; deployfleet_ui stays a lightweight, foundational
 * UI kit rather than hard-depending on the entire business layer).
 */
export class DeployfleetMissionControl extends Component {
    static template = "deployfleet_ui.MissionControl";
    static components = { DeployfleetStatusPill, DeployfleetMetricCard, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately: this is an
    // `ir.actions.client` root component, and Odoo's action manager
    // always injects standard props (`action`, `actionId`,
    // `updateActionState`, `className`, ...) into whatever component it
    // mounts. Declaring `static props = {}` here previously told OWL
    // this component accepts zero props, which made it reject every one
    // of those injected props and crash on mount
    // ("Invalid props ... unknown key 'action'..."). Omitting `props`
    // entirely (the same pattern already used by the working Component
    // Showcase and Domain Mega Menu actions) skips prop validation for
    // this component instead.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            unassignedShipments: 0,
            expiringDocuments: 0,
            expiredDocuments: 0,
            breakdownVehicles: 0,
            pendingApprovals: 0,
            activeVehicles: 0,
            activeShipments: 0,
            confirmedRevenue: 0,
            setupItemsTotal: 0,
            setupItemsDone: 0,
            setupStripDismissed: false,
            // sessionStorage, not localStorage: demo accounts are one
            // shared login used by many different real visitors, so the
            // welcome card should reappear on every fresh login, but not
            // re-flash every time someone navigates back to Mission
            // Control mid-session.
            welcomeDismissed: window.sessionStorage.getItem(SESSION_STORAGE_KEY) === "1",
        });
        this.demoRole = getDemoRole();

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await this._loadCounts();
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async _loadCounts() {
        const [
            unassignedShipments,
            expiringDocuments,
            expiredDocuments,
            breakdownVehicles,
            pendingApprovals,
            activeVehicles,
            activeShipments,
            confirmedInvoices,
            setupItemsTotal,
            setupItemsDone,
        ] = await Promise.all([
            this.orm.searchCount("deployfleet.shipment", [["state", "=", "confirmed"]]),
            this.orm.searchCount("deployfleet.compliance.document", [["state", "=", "expiring_soon"]]),
            this.orm.searchCount("deployfleet.compliance.document", [["state", "=", "expired"]]),
            this.orm.searchCount("deployfleet.vehicle", [["status", "=", "breakdown"]]),
            this.orm.searchCount("deployfleet.ai.action.request", [["state", "=", "pending_approval"]]),
            this.orm.searchCount("deployfleet.vehicle", [["status", "in", ["available", "assigned"]]]),
            this.orm.searchCount(
                "deployfleet.shipment",
                [["state", "in", ["confirmed", "assigned", "in_transit"]]],
            ),
            this.orm.searchRead("deployfleet.invoice", [["state", "=", "confirmed"]], ["amount_total"]),
            // First-Time Experience checklist (doc 22) - the one existing-
            // screen touch the Help Center feature makes. Own group,
            // deployfleet.help.checklist.progress rows are already scoped
            // to the current user by the backend's own ir.rule.
            this.orm.searchCount("deployfleet.help.checklist.item", []),
            this.orm.searchCount("deployfleet.help.checklist.progress", [["done", "=", true]]),
        ]);

        this.state.unassignedShipments = unassignedShipments;
        this.state.expiringDocuments = expiringDocuments;
        this.state.expiredDocuments = expiredDocuments;
        this.state.breakdownVehicles = breakdownVehicles;
        this.state.pendingApprovals = pendingApprovals;
        this.state.activeVehicles = activeVehicles;
        this.state.activeShipments = activeShipments;
        this.state.confirmedRevenue = confirmedInvoices.reduce((sum, invoice) => sum + invoice.amount_total, 0);
        this.state.setupItemsTotal = setupItemsTotal;
        this.state.setupItemsDone = setupItemsDone;
    }

    get showSetupStrip() {
        return (
            !this.demoRole &&
            !this.state.setupStripDismissed &&
            this.state.setupItemsTotal > 0 &&
            this.state.setupItemsDone < this.state.setupItemsTotal
        );
    }

    onDismissSetupStrip() {
        this.state.setupStripDismissed = true;
    }

    onContinueSetup() {
        this.actionService.doAction("deployfleet_ui.action_deployfleet_help_center", { clearBreadcrumbs: true });
    }

    get welcomeContent() {
        return this.demoRole ? DEMO_ROLE_CONTENT[this.demoRole] : null;
    }

    get showWelcomeCard() {
        // Guards against an unrecognized role (e.g. "customer", which
        // never actually reaches Mission Control - portal users get a
        // different UI surface entirely - but defensively checked here
        // rather than assumed): DEMO_ROLE_CONTENT has no entry for it,
        // so welcomeContent would be null and the template would throw
        // reading .heading off it.
        return Boolean(this.welcomeContent) && !this.state.welcomeDismissed;
    }

    onDismissWelcome() {
        this.state.welcomeDismissed = true;
        window.sessionStorage.setItem(SESSION_STORAGE_KEY, "1");
    }

    onWelcomeLinkClick(link) {
        this.actionService.doAction(link.actionXmlId, { clearBreadcrumbs: true });
    }

    get formattedRevenue() {
        return this.state.confirmedRevenue.toLocaleString(undefined, { maximumFractionDigits: 0 });
    }

    get attentionPills() {
        return ATTENTION_ITEMS.map((item) => ({ ...item, count: this.state[item.stateKey] })).filter(
            (item) => item.count > 0,
        );
    }

    get hasAttentionItems() {
        return this.attentionPills.length > 0;
    }

    get quickLinks() {
        return DOMAIN_QUICK_LINKS;
    }

    onAttentionPillClick(actionXmlId) {
        this.actionService.doAction(actionXmlId, { clearBreadcrumbs: true });
    }

    onQuickLinkClick(link) {
        this.actionService.doAction(link.actionXmlId, { clearBreadcrumbs: true });
    }
}

registry.category("actions").add("deployfleet_ui.mission_control", DeployfleetMissionControl);
