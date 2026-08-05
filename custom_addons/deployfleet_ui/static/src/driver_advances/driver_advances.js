/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "issued", label: "Issued" },
    { key: "reconciled", label: "Reconciled" },
    { key: "deducted", label: "Deducted" },
];

const STATE_LABEL = { issued: "Issued", reconciled: "Reconciled", deducted: "Deducted" };
const STATE_BADGE_VARIANT = { issued: "info", reconciled: "warning", deducted: "success" };

const PURPOSE_LABEL = {
    fuel: "Fuel",
    toll_border: "Toll / Border Fee",
    subsistence: "Subsistence",
    other: "Other",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Driver Advances (Driver & HR domain custom-views work) — a
 * fleet-wide advances ledger, replacing the stock
 * `deployfleet.driver.advance` list/form. Same rationale as the Tyre
 * Manager/Insurance Center precedent from Fleet & Vehicles: advances
 * are driver-linked, and Driver Scorecards already shows one driver's
 * own advances in context, but a fleet-wide "who has outstanding
 * advances right now" view is a distinct planning workflow neither the
 * stock list nor the per-driver detail supports.
 *
 * Registry-ledger visual language (header row, table rows, right-
 * aligned tabular-nums figures) — a ledger to scan, not an operational
 * review queue, matching the Parts/Asset Registry precedent. Filter
 * chips by state; tap-to-expand reveals reconciled-expense lines and
 * the real state-transition actions (`action_mark_reconciled()`,
 * `action_mark_deducted()`) — `issued -> reconciled -> deducted` is a
 * strictly linear state machine with no reject/cancel path, confirmed
 * from source before building this.
 *
 * Soft-coupling: `deployfleet.driver.advance` is referenced as a plain
 * runtime string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetDriverAdvances extends Component {
    static template = "deployfleet_ui.DriverAdvances";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            advances: [],
            stateFilter: "all",
            selectedAdvanceId: null,
            expensesByAdvanceId: {},
            actingId: null,
        });

        onWillStart(() => this.loadAdvances());
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.advances.length
                    : this.state.advances.filter((a) => a.state === filter.key).length,
        }));
    }

    get filteredAdvances() {
        if (this.state.stateFilter === "all") {
            return this.state.advances;
        }
        return this.state.advances.filter((a) => a.state === this.state.stateFilter);
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    purposeLabel(purpose) {
        return PURPOSE_LABEL[purpose] || purpose;
    }

    async loadAdvances() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            this.state.advances = await this.orm.searchRead(
                "deployfleet.driver.advance",
                [],
                ["driver_id", "purpose", "issued_date", "amount", "outstanding_amount", "state"],
                { order: "issued_date desc" },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectAdvance(advanceId) {
        if (this.state.selectedAdvanceId === advanceId) {
            this.state.selectedAdvanceId = null;
            return;
        }
        this.state.selectedAdvanceId = advanceId;
        if (!this.state.expensesByAdvanceId[advanceId]) {
            const expenses = await this.orm.searchRead(
                "deployfleet.load.expense",
                [["advance_id", "=", advanceId]],
                ["expense_type", "amount"],
            );
            this.state.expensesByAdvanceId[advanceId] = expenses;
        }
    }

    async onAdvanceAction(advanceId, method) {
        this.state.actingId = advanceId;
        try {
            await this.orm.call("deployfleet.driver.advance", method, [[advanceId]]);
            await this.loadAdvances();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }
}

registry.category("actions").add("deployfleet_ui.driver_advances", DeployfleetDriverAdvances);
