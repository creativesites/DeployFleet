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
    { key: "submitted", label: "Submitted" },
    { key: "accepted", label: "Accepted" },
    { key: "rejected", label: "Rejected" },
    { key: "error", label: "Error" },
];

const STATE_BADGE_VARIANT = {
    draft: "info", submitted: "info", accepted: "success", rejected: "danger", error: "danger",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * ZRA Compliance (Billing & Finance domain) — replaces
 * `deployfleet.zra.submission`'s stock list/form with a state-filterable
 * ledger plus the company's device configuration status at a glance.
 *
 * Per the domain-audit decision: dispatcher's ACL on this model stays
 * read-only exactly as it was (a deliberate confidentiality/oversight
 * gate, not a bug — same reading as the Insurance Claim precedent). The
 * Retry button stays visible to every role and simply surfaces a
 * friendly notification on an AccessError, the same "a view restriction
 * is a UI convenience, not a security boundary" pattern the Insurance
 * Center's own claim-action buttons already established — this screen
 * deliberately does not invent new client-side role-detection to hide
 * the button instead.
 *
 * ZRA's own endpoint/field sourcing (a community Postman collection, not
 * ZRA's own verified spec — see deployfleet_zra's README) is unchanged
 * by this screen; this makes what already exists visible, it is not a
 * sign-off on the integration itself.
 *
 * Soft-coupling: `deployfleet.zra.submission`/`.zra.config` are
 * referenced as plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetZraCompliance extends Component {
    static template = "deployfleet_ui.ZraCompliance";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            submissions: [],
            config: null,
            stateFilter: "all",
            selectedSubmissionId: null,
            retryingSubmissionId: null,
        });

        onWillStart(() => this.loadAllInitialData());
    }

    async loadAllInitialData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await Promise.all([this.loadSubmissions(), this.loadConfig()]);
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
                    ? this.state.submissions.length
                    : this.state.submissions.filter((submission) => submission.state === filter.key).length,
        }));
    }

    get filteredSubmissions() {
        if (this.state.stateFilter === "all") {
            return this.state.submissions;
        }
        return this.state.submissions.filter((submission) => submission.state === this.state.stateFilter);
    }

    async loadSubmissions() {
        this.state.submissions = await this.orm.searchRead(
            "deployfleet.zra.submission",
            [],
            ["invoice_id", "state", "zra_receipt_no", "error_message", "submitted_date"],
            { order: "create_date desc" },
        );
    }

    async loadConfig() {
        const configs = await this.orm.searchRead(
            "deployfleet.zra.config", [], ["environment", "tpin", "branch_id", "initialized"], { limit: 1 },
        );
        this.state.config = configs[0] || null;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    onSelectSubmission(submissionId) {
        this.state.selectedSubmissionId = this.state.selectedSubmissionId === submissionId ? null : submissionId;
    }

    async onRetrySubmission(submissionId) {
        this.state.retryingSubmissionId = submissionId;
        try {
            await this.orm.call("deployfleet.zra.submission", "action_submit", [[submissionId]]);
            await this.loadSubmissions();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.retryingSubmissionId = null;
        }
    }

    onOpenInvoiceForm(invoiceId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.invoice",
            res_id: invoiceId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.zra_compliance", DeployfleetZraCompliance);
