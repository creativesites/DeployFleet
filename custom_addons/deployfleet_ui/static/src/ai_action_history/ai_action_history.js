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
    { key: "draft", label: "Draft" },
    { key: "pending_approval", label: "Pending" },
    { key: "approved", label: "Approved" },
    { key: "rejected", label: "Rejected" },
    { key: "executed", label: "Executed" },
    { key: "failed", label: "Failed" },
];

const STATE_LABEL = {
    draft: "Draft",
    pending_approval: "Pending Approval",
    approved: "Approved",
    rejected: "Rejected",
    executed: "Executed",
    failed: "Failed",
};

const STATE_BADGE_VARIANT = {
    draft: "info",
    pending_approval: "warning",
    approved: "info",
    rejected: "danger",
    executed: "success",
    failed: "danger",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function formatProposedVals(proposedVals) {
    try {
        return JSON.stringify(JSON.parse(proposedVals), null, 2);
    } catch {
        return proposedVals;
    }
}

/**
 * AI Action History (AI & Intelligence domain) — a fleet-wide,
 * filterable history/audit view over `deployfleet.ai.action.request`,
 * built per the user's explicit choice during this domain's design
 * conversation. The Copilot Rail's own ambient queue only ever shows
 * `pending_approval` items (by design, per its own doc comments); there
 * was no way to browse approved/rejected/executed/failed history
 * anywhere in the product before this — a real gap for the same reason
 * the AI & Intelligence audit flagged it: `group_deployfleet_
 * system_auditor` was just given read access to this exact model (see
 * CLAUDE.md's AI & Intelligence writeup) specifically because auditing
 * this trail is squarely the role's purpose, and it had nowhere custom
 * to actually look.
 *
 * Same filter-chips-plus-accordion pattern as the Trip Board/Workshop
 * Board, extended to all six states rather than an "active vs.
 * terminal" split, since a full history browse is this screen's whole
 * point. Approve/Reject on a still-pending row reuse the exact same
 * `action_approve`/`action_reject` calls the Copilot Rail already
 * makes — this screen doesn't duplicate that logic, just gives it a
 * second, filterable/searchable home for users who'd rather browse a
 * full page than the Rail's compact queue.
 *
 * Soft-coupling: `deployfleet.ai.action.request` is referenced as a
 * plain runtime string, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetAiActionHistory extends Component {
    static template = "deployfleet_ui.AiActionHistory";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            requests: [],
            stateFilter: "all",
            selectedRequestId: null,
            actingRequestId: null,
            rejectReasonByRequestId: {},
        });

        onWillStart(() => this.loadRequests());
    }

    async loadRequests() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            this.state.requests = await this.orm.searchRead(
                "deployfleet.ai.action.request",
                [],
                [
                    // action_method/auto_executed added per the engineering-audit
                    // fix: this screen shows every state, including executed
                    // ones, so both the real effect of an action_method request
                    // (proposed_vals is typically {} for that shape) and whether
                    // a human ever actually reviewed it belong here.
                    "name", "feature_id", "action_type", "target_model", "target_id", "proposed_vals",
                    "action_method", "auto_executed", "source_context", "state", "requested_by",
                    "approved_by", "executed_at", "rejection_reason", "error_message",
                    "result_record_id", "create_date",
                ],
                { order: "create_date desc" },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.requests.length
                    : this.state.requests.filter((r) => r.state === filter.key).length,
        }));
    }

    get filteredRequests() {
        if (this.state.stateFilter === "all") {
            return this.state.requests;
        }
        return this.state.requests.filter((r) => r.state === this.state.stateFilter);
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    formattedProposedVals(proposedVals) {
        return formatProposedVals(proposedVals);
    }

    onSelectRequest(requestId) {
        this.state.selectedRequestId = this.state.selectedRequestId === requestId ? null : requestId;
    }

    async onApprove(requestId) {
        this.state.actingRequestId = requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_approve", [[requestId]]);
            await this.loadRequests();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }

    onRejectReasonInput(requestId, value) {
        this.state.rejectReasonByRequestId[requestId] = value;
    }

    async onReject(requestId) {
        const reason = (this.state.rejectReasonByRequestId[requestId] || "").trim();
        if (!reason) {
            this.notification.add("A rejection reason is required.", { type: "danger" });
            return;
        }
        this.state.actingRequestId = requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_reject", [[requestId], reason]);
            delete this.state.rejectReasonByRequestId[requestId];
            await this.loadRequests();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }
}

registry.category("actions").add("deployfleet_ui.ai_action_history", DeployfleetAiActionHistory);
