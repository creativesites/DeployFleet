/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";
import { DEPLOYFLEET_MEGA_MENU_DOMAINS } from "../mega_menu/domain_content";

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
    static components = { DeployfleetStatusPill, DeployfleetMetricCard };
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
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        const [
            unassignedShipments,
            expiringDocuments,
            expiredDocuments,
            breakdownVehicles,
            pendingApprovals,
            activeVehicles,
            activeShipments,
            confirmedInvoices,
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
        ]);

        this.state.unassignedShipments = unassignedShipments;
        this.state.expiringDocuments = expiringDocuments;
        this.state.expiredDocuments = expiredDocuments;
        this.state.breakdownVehicles = breakdownVehicles;
        this.state.pendingApprovals = pendingApprovals;
        this.state.activeVehicles = activeVehicles;
        this.state.activeShipments = activeShipments;
        this.state.confirmedRevenue = confirmedInvoices.reduce((sum, invoice) => sum + invoice.amount_total, 0);
        this.state.loading = false;
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
