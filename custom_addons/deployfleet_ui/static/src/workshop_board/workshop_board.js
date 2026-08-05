/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const STATE_FILTERS = [
    { key: "all", label: "Active" },
    { key: "open", label: "Open" },
    { key: "diagnosis", label: "Diagnosis" },
    { key: "repair", label: "Repair" },
    { key: "approval", label: "Approval" },
    { key: "closed", label: "Closed" },
];

const STATE_BADGE_VARIANT = {
    open: "info",
    diagnosis: "info",
    repair: "warning",
    approval: "warning",
    closed: "success",
};

const STATE_LABEL = {
    open: "Open",
    diagnosis: "Diagnosis",
    repair: "Repair",
    approval: "Pending Approval",
    closed: "Closed",
};

// The action method to call for a job card currently in a given state —
// mirrors deployfleet.workshop.job.card's real state machine
// (open -> diagnosis -> repair -> approval -> closed) one-to-one.
const NEXT_ACTION_BY_STATE = {
    open: { method: "action_start_diagnosis", label: "Start Diagnosis" },
    diagnosis: { method: "action_start_repair", label: "Start Repair" },
    repair: { method: "action_submit_for_approval", label: "Submit for Approval" },
    approval: { method: "action_close", label: "Close" },
};

const LINE_TYPE_LABEL = {
    labor: "Labor",
    part: "Part",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * The Workshop Board (doc 16 §7.12, Fleet & Vehicles domain) — the
 * workshop supervisor's primary workspace: every open job card, grouped
 * by its real state, with one-tap progression through the state machine.
 *
 * **Deliberately tap-to-expand with state-filter chips, not a literal
 * multi-column drag-drop kanban**, even though doc 16 §7.12's original
 * description says "a job-card kanban board." Same reasoning already
 * established for the Dispatch Board (§7.9): a multi-column kanban is
 * inherently a wide-viewport pattern, and CLAUDE.md's mobile-first
 * mandate applies here without exception. This reuses the exact
 * filter-chips-plus-accordion pattern the Dispatch Board, Fleet Command
 * Center, and Driver Scorecards already established and verified works
 * on mobile, rather than inventing a new interaction model for one
 * screen. State transitions happen via real one-tap buttons calling
 * `deployfleet.workshop.job.card`'s actual, unmodified action methods
 * (`action_start_diagnosis` -> `action_start_repair` ->
 * `action_submit_for_approval` -> `action_close`) — the same five-state
 * machine the backend already enforces (`_check_state()` raises if a
 * card isn't in the expected state), not reinvented here.
 *
 * "Active" (the default filter) excludes closed jobs, the same
 * established convention as Fleet Command Center excluding retired
 * vehicles from its own "All" default — closed job cards are history,
 * not something a supervisor needs to see by default. A "Closed" chip
 * is still available to review history.
 *
 * Job lines (labor/parts) render read-only in the expanded detail —
 * consistent with every other slice in this module, no screen here lets
 * a user edit arbitrary fields inline; "Open full record" is where line
 * items get added or edited.
 *
 * Workspace Layer: sustained operational work, not a launch/orientation
 * screen, the same reasoning as the Dispatch Board and Fleet Command
 * Center.
 *
 * Soft-coupling: deployfleet.workshop.job.card/job.line are referenced
 * as plain runtime strings, the same decision made throughout
 * deployfleet_ui.
 */
export class DeployfleetWorkshopBoard extends Component {
    static template = "deployfleet_ui.WorkshopBoard";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration — see the identical comment in
    // mission_control.js: this is an `ir.actions.client` root component,
    // and Odoo's action manager always injects standard props into it.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            jobCards: [],
            lineIdsByJobCardId: {},
            selectedJobCardId: null,
            stateFilter: "all",
            transitioningJobCardId: null,
        });

        onWillStart(() => this.loadJobCards());
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.jobCards.filter((job) => job.state !== "closed").length
                    : this.state.jobCards.filter((job) => job.state === filter.key).length,
        }));
    }

    get filteredJobCards() {
        if (this.state.stateFilter === "all") {
            return this.state.jobCards.filter((job) => job.state !== "closed");
        }
        return this.state.jobCards.filter((job) => job.state === this.state.stateFilter);
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    lineTypeLabel(lineType) {
        return LINE_TYPE_LABEL[lineType] || lineType;
    }

    nextAction(state) {
        return NEXT_ACTION_BY_STATE[state] || null;
    }

    async loadJobCards() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const jobCards = await this.orm.searchRead(
                "deployfleet.workshop.job.card",
                [],
                ["name", "vehicle_id", "description", "opened_date", "total_cost", "state"],
                { order: "opened_date asc" },
            );
            this.state.jobCards = jobCards;
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectJobCard(jobCardId) {
        if (this.state.selectedJobCardId === jobCardId) {
            this.state.selectedJobCardId = null;
            return;
        }
        this.state.selectedJobCardId = jobCardId;
        if (!this.state.lineIdsByJobCardId[jobCardId]) {
            const lines = await this.orm.searchRead(
                "deployfleet.workshop.job.line",
                [["job_card_id", "=", jobCardId]],
                ["line_type", "part_id", "description", "quantity", "unit_cost", "subtotal"],
            );
            this.state.lineIdsByJobCardId[jobCardId] = lines;
        }
    }

    async onAdvanceState(jobCard) {
        const action = this.nextAction(jobCard.state);
        if (!action) {
            return;
        }
        this.state.transitioningJobCardId = jobCard.id;
        try {
            await this.orm.call("deployfleet.workshop.job.card", action.method, [[jobCard.id]]);
            await this.loadJobCards();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.transitioningJobCardId = null;
        }
    }

    onOpenJobCardForm(jobCardId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.workshop.job.card",
            res_id: jobCardId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.workshop_board", DeployfleetWorkshopBoard);
