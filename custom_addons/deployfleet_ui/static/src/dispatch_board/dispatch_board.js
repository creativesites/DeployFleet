/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";

// A shipment is "urgent" once its requested pickup is less than this many
// hours away — mirrors no backend field, this is a pure display heuristic
// (doc 16 §7.9) to help a dispatcher triage a long list at a glance.
const URGENT_WINDOW_HOURS = 24;

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * The Dispatch Board (doc 16 §3.5/§7.9, Phase C / Slice 2) — the
 * dispatcher's primary workspace: confirmed shipments awaiting a
 * driver/vehicle assignment, ranked candidate suggestions, and a
 * confirm-with-override path when the backend demands a reason.
 *
 * Deliberately **Workspace Layer** (flat, light, high-contrast; see
 * dispatch_board.scss), unlike every other Phase B/C screen built so far
 * (Mission Control, Mega Menus, Launcher are all Command Layer dark
 * glass). Doc 16 Principle 1 is explicit that sustained-work screens — a
 * dispatcher stares at this one for a full shift — must not fight a
 * translucent card for contrast the way an orientation/launch screen can
 * afford to.
 *
 * Deliberately **tap-to-assign, not drag-and-drop**: doc 16 originally
 * envisioned a DeployGuard-style drag interaction for assigning a
 * candidate to a shipment, but HTML5 drag-and-drop has poor touch-device
 * support, and CLAUDE.md's mobile-first mandate applies to every Phase C
 * screen without exception. Tap-to-expand plus a "Confirm" button ships
 * the exact same underlying action (propose -> confirm) without depending
 * on an interaction model touch devices can't reliably perform. Desktop
 * drag-and-drop remains a valid future progressive enhancement, not a
 * reversal of this decision.
 *
 * Backend contract note: `deployfleet.dispatch.assignment.action_confirm()`
 * is a plain `UserError`-raising method (see deployfleet_dispatch and
 * deployfleet_dispatch_compliance), not a structured
 * {success, hard_block, override_required} response the way doc 16's
 * DeployGuard-derived description reads. This component reconciles that:
 * it calls `action_confirm`, and on failure opens an override dialog that
 * writes the same operator-supplied reason to both `override_reason`
 * (deployfleet_dispatch) and `compliance_override_reason`
 * (deployfleet_dispatch_compliance) before retrying — one reason covers
 * either backend check without the frontend needing to parse the error
 * message to tell them apart.
 *
 * Soft-coupling: deployfleet.shipment/deployfleet.dispatch.assignment are
 * referenced as plain runtime strings, the same decision already made for
 * the Mega Menu tiles, Command Palette search, and Mission Control's
 * counts — deployfleet_ui stays a lightweight UI kit with no hard
 * manifest dependency on deployfleet_dispatch.
 */
export class DeployfleetDispatchBoard extends Component {
    static template = "deployfleet_ui.DispatchBoard";
    static components = { DeployfleetButton, DeployfleetStatusBadge };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            shipments: [],
            candidatesByShipment: {},
            selectedShipmentId: null,
            suggestingShipmentId: null,
            confirmingAssignmentId: null,
            overrideDialog: null,
        });

        onWillStart(() => this.loadShipments());
    }

    computeUrgency(pickupDate) {
        if (!pickupDate) {
            return null;
        }
        // Odoo datetimes come back as "YYYY-MM-DD HH:MM:SS" UTC.
        const pickupMs = new Date(pickupDate.replace(" ", "T") + "Z").getTime();
        const hoursUntilPickup = (pickupMs - Date.now()) / (1000 * 60 * 60);
        if (hoursUntilPickup < 0) {
            return "danger";
        }
        if (hoursUntilPickup <= URGENT_WINDOW_HOURS) {
            return "warning";
        }
        return null;
    }

    async loadShipments() {
        this.state.loading = true;
        const shipments = await this.orm.searchRead(
            "deployfleet.shipment",
            [["state", "=", "confirmed"]],
            ["name", "customer_id", "pickup_depot_id", "dropoff_depot_id", "requested_pickup_date", "weight_kg"],
            { order: "requested_pickup_date asc" },
        );
        this.state.shipments = shipments.map((shipment) => ({
            ...shipment,
            urgency: this.computeUrgency(shipment.requested_pickup_date),
        }));
        this.state.loading = false;
    }

    async onSelectShipment(shipmentId) {
        if (this.state.selectedShipmentId === shipmentId) {
            this.state.selectedShipmentId = null;
            return;
        }
        this.state.selectedShipmentId = shipmentId;
        if (!this.state.candidatesByShipment[shipmentId]) {
            await this.loadCandidates(shipmentId);
        }
    }

    async loadCandidates(shipmentId) {
        const candidates = await this.orm.searchRead(
            "deployfleet.dispatch.assignment",
            [["shipment_id", "=", shipmentId], ["state", "=", "proposed"]],
            ["driver_id", "vehicle_id", "score"],
            { order: "score desc" },
        );
        this.state.candidatesByShipment[shipmentId] = candidates;
    }

    async onSuggestAssignments(shipmentId) {
        this.state.suggestingShipmentId = shipmentId;
        try {
            await this.orm.call("deployfleet.shipment", "action_suggest_assignments", [[shipmentId]]);
            await this.loadCandidates(shipmentId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.suggestingShipmentId = null;
        }
    }

    async onConfirmCandidate(shipmentId, assignmentId) {
        this.state.confirmingAssignmentId = assignmentId;
        try {
            await this.orm.call("deployfleet.dispatch.assignment", "action_confirm", [[assignmentId]]);
            await this.loadShipments();
            delete this.state.candidatesByShipment[shipmentId];
            this.state.selectedShipmentId = null;
        } catch (error) {
            this.state.overrideDialog = {
                shipmentId,
                assignmentId,
                reasonText: "",
                errorMessage: extractErrorMessage(error),
            };
        } finally {
            this.state.confirmingAssignmentId = null;
        }
    }

    onOverrideReasonInput(ev) {
        if (this.state.overrideDialog) {
            this.state.overrideDialog.reasonText = ev.target.value;
        }
    }

    onCancelOverride() {
        this.state.overrideDialog = null;
    }

    async onSubmitOverride() {
        const dialog = this.state.overrideDialog;
        if (!dialog || !dialog.reasonText.trim()) {
            return;
        }
        try {
            await this.orm.write("deployfleet.dispatch.assignment", [dialog.assignmentId], {
                override_reason: dialog.reasonText,
                compliance_override_reason: dialog.reasonText,
            });
            await this.orm.call("deployfleet.dispatch.assignment", "action_confirm", [[dialog.assignmentId]]);
            this.state.overrideDialog = null;
            await this.loadShipments();
            delete this.state.candidatesByShipment[dialog.shipmentId];
            this.state.selectedShipmentId = null;
        } catch (error) {
            this.state.overrideDialog.errorMessage = extractErrorMessage(error);
        }
    }

    onOpenShipmentForm(shipmentId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.shipment",
            res_id: shipmentId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.dispatch_board", DeployfleetDispatchBoard);
