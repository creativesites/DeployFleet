/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { DeployfleetButton } from "../components/button/button";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * The Copilot Rail (doc 16 §6/§8, Phase C / Slice 4) — a persistent,
 * collapsed-by-default docked panel present across every workspace,
 * violet-accented per doc 17's AI-content convention, never auto-executing
 * anything per the mandatory suggestion -> approval -> execute pipeline
 * ([08-ai-architecture.md](../../../../../docs/architecture/08-ai-architecture.md) §5,
 * CLAUDE.md §4, hard risk #7).
 *
 * **Scope note, same transparency discipline as every other Phase C
 * slice:** doc 16 §419 places the Copilot Console deliberately at the
 * Phase C/D boundary — the *ambient* half (this rail, plus AI
 * Recommendation Cards inline on flagship screens) belongs in Phase C;
 * the *destination* half (a dedicated Copilot Console screen with an
 * agent catalog and a usage/cost dashboard over `deployfleet.ai.usage`)
 * is explicitly allowed to trail into Phase D. This slice ships exactly
 * the ambient half: a live pending-approvals badge and an expandable
 * queue wired to the real `deployfleet.ai.action.request` pipeline
 * (`action_approve()`/`action_reject()`, unchanged) — real, working
 * approve/reject, not a mockup. **Not yet built:** per-record contextual
 * awareness (showing agent output specific to whatever record is
 * currently open — the rail always shows the same global queue
 * regardless of what page it's opened from), a natural-language question
 * interface, the agent catalog view, and the usage/cost dashboard — all
 * explicitly deferred to the Phase D Copilot Console per doc 16's own
 * boundary, not silently dropped.
 *
 * `Alt+A` is a new keybinding, chosen the same way the Launcher's
 * per-domain shortcuts were: it doesn't collide with any binding already
 * claimed (L, D, F, C, B, R, I, H).
 *
 * Soft-coupling: deployfleet.ai.action.request is referenced as a plain
 * runtime string, the same decision made throughout deployfleet_ui.
 */
export class DeployfleetCopilotRail extends Component {
    static template = "deployfleet_ui.CopilotRail";
    static components = { DeployfleetButton };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            open: false,
            loading: true,
            pendingApprovals: [],
            actingRequestId: null,
            rejectDialog: null,
        });

        useHotkey("alt+a", () => this.toggleOpen(), { global: true, allowRepeat: false });
        useHotkey(
            "escape",
            () => {
                if (this.state.open) {
                    this.close();
                }
            },
            { global: true, allowRepeat: false },
        );

        onWillStart(() => this.loadPendingApprovals());
    }

    async loadPendingApprovals() {
        this.state.loading = true;
        this.state.pendingApprovals = await this.orm.searchRead(
            "deployfleet.ai.action.request",
            [["state", "=", "pending_approval"]],
            ["name", "feature_id", "action_type", "target_model", "proposed_vals", "requested_by"],
            { order: "create_date asc" },
        );
        this.state.loading = false;
    }

    get pendingCount() {
        return this.state.pendingApprovals.length;
    }

    formattedProposedVals(proposedVals) {
        try {
            return JSON.stringify(JSON.parse(proposedVals), null, 2);
        } catch {
            return proposedVals;
        }
    }

    toggleOpen() {
        if (this.state.open) {
            this.close();
        } else {
            this.state.open = true;
            this.loadPendingApprovals();
        }
    }

    close() {
        this.state.open = false;
        this.state.rejectDialog = null;
    }

    async onApprove(requestId) {
        this.state.actingRequestId = requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_approve", [[requestId]]);
            await this.loadPendingApprovals();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }

    onOpenRejectDialog(requestId) {
        this.state.rejectDialog = { requestId, reasonText: "" };
    }

    onRejectReasonInput(ev) {
        if (this.state.rejectDialog) {
            this.state.rejectDialog.reasonText = ev.target.value;
        }
    }

    onCancelReject() {
        this.state.rejectDialog = null;
    }

    async onConfirmReject() {
        const dialog = this.state.rejectDialog;
        if (!dialog) {
            return;
        }
        this.state.actingRequestId = dialog.requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_reject", [
                [dialog.requestId],
                dialog.reasonText,
            ]);
            this.state.rejectDialog = null;
            await this.loadPendingApprovals();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }
}

registry.category("main_components").add("deployfleet_ui.CopilotRail", {
    Component: DeployfleetCopilotRail,
});
