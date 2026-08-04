/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { useCopilotContext } from "../copilot_rail/copilot_context";

// A shipment is "urgent" once its requested pickup is less than this many
// hours away — mirrors no backend field, this is a pure display heuristic
// (doc 16 §7.9) to help a dispatcher triage a long list at a glance.
const URGENT_WINDOW_HOURS = 24;

const STATE_FILTERS = [
    { key: "active", label: "Active" },
    { key: "draft", label: "Draft" },
    { key: "confirmed", label: "Confirmed" },
    { key: "assigned", label: "Assigned" },
    { key: "in_transit", label: "In Transit" },
    { key: "delivered", label: "Delivered" },
    { key: "cancelled", label: "Cancelled" },
];

const STATE_LABEL = {
    draft: "Draft",
    confirmed: "Confirmed",
    assigned: "Assigned",
    in_transit: "In Transit",
    delivered: "Delivered",
    cancelled: "Cancelled",
};

const STATE_BADGE_VARIANT = {
    draft: "info",
    confirmed: "info",
    assigned: "warning",
    in_transit: "warning",
    delivered: "success",
    cancelled: "info",
};

// States a dispatcher can still call action_cancel() from through this
// workspace. The backend method itself has no state guard at all (it
// always cancels), but offering a Cancel button once a shipment is
// in_transit/delivered/cancelled would invite misuse a real dispatcher
// workflow doesn't want — proof-of-delivery is the correct undo path
// past that point, not a raw state flip.
const CANCELLABLE_STATES = new Set(["draft", "confirmed", "assigned"]);

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function toOdooDatetime(localValue) {
    // <input type="datetime-local"> yields "YYYY-MM-DDTHH:MM" (local time,
    // no seconds/zone); Odoo's Datetime fields want "YYYY-MM-DD HH:MM:SS".
    // This module has no timezone-conversion precedent anywhere else
    // (every prior date field has been a plain Date, not a Datetime), so
    // the value is sent as-is with seconds appended — good enough for a
    // quick-add form field a dispatcher can always edit precisely on the
    // full record.
    return localValue ? `${localValue.replace("T", " ")}:00` : false;
}

/**
 * The Dispatch Board (doc 16 §3.5/§7.9, Phase C / Slice 2) — the
 * dispatcher's primary workspace. Originally scoped to just the
 * confirmed-shipment-to-assignment matching step; evolved during the
 * Dispatch & Trips domain audit (docs/architecture/20-experience-
 * implementation-strategy.md §6c) into the full shipment lifecycle —
 * booking a new shipment, tracking it through every state, and the
 * existing suggest/confirm/override matching flow — rather than building
 * a second "Shipments" screen alongside it. Same "evolve the existing
 * screen" choice as Fleet Command Center absorbing the Vehicle Profile
 * and Driver Scorecards absorbing Driver 360.
 *
 * State filter chips (Active/Draft/Confirmed/Assigned/In Transit/
 * Delivered/Cancelled) reuse the Workshop Board's "Active excludes
 * terminal states by default" convention — Delivered/Cancelled are
 * history, not something a dispatcher needs to see by default.
 *
 * Per-state detail: draft shipments get Confirm/Cancel; confirmed
 * shipments keep the original suggest-assignments/confirm/override flow
 * unchanged; assigned/in_transit/delivered shipments show the confirmed
 * assignment's driver/vehicle read-only, with a pointer to Trip Board /
 * Delivery Center for what happens next — this screen deliberately does
 * not duplicate trip departure/completion or POD capture, both of which
 * now have their own dedicated workspaces.
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
 * message to tell them apart. As of this evolution, that same backend
 * scoring also disqualifies a driver on approved leave overlapping the
 * requested pickup date (deployfleet_dispatch_compliance) — this screen
 * needs no changes for that, since it only ever sees whichever candidates
 * the backend already scored as eligible.
 *
 * Soft-coupling: deployfleet.shipment/deployfleet.dispatch.assignment/
 * deployfleet.depot/deployfleet.vehicle.type are referenced as plain
 * runtime strings, the same decision already made for the Mega Menu
 * tiles, Command Palette search, and Mission Control's counts —
 * deployfleet_ui stays a lightweight UI kit with no hard manifest
 * dependency on deployfleet_dispatch.
 */
export class DeployfleetDispatchBoard extends Component {
    static template = "deployfleet_ui.DispatchBoard";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component, and declaring an empty props schema here made OWL
    // reject the standard props (`action`, `actionId`,
    // `updateActionState`, `className`, ...) Odoo's action manager always
    // injects, crashing on mount.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.copilotContext = useCopilotContext();
        this.state = useState({
            loading: true,
            shipments: [],
            depots: [],
            vehicleTypes: [],
            customers: [],
            candidatesByShipment: {},
            assignmentInfoByShipment: {},
            selectedShipmentId: null,
            stateFilter: "active",
            suggestingShipmentId: null,
            confirmingAssignmentId: null,
            actingShipmentId: null,
            overrideDialog: null,
            newShipment: {
                customer_id: "", pickup_depot_id: "", dropoff_depot_id: "",
                requested_pickup_date: "", cargo_description: "", weight_kg: "", required_vehicle_type_id: "",
            },
            creating: false,
        });

        onWillStart(() =>
            Promise.all([this.loadShipments(), this.loadFormData()])
        );
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
            [],
            [
                "name", "customer_id", "pickup_depot_id", "dropoff_depot_id",
                "requested_pickup_date", "weight_kg", "state",
            ],
            { order: "requested_pickup_date asc" },
        );
        this.state.shipments = shipments.map((shipment) => ({
            ...shipment,
            urgency: this.computeUrgency(shipment.requested_pickup_date),
        }));
        this.state.loading = false;
    }

    async loadFormData() {
        const [depots, vehicleTypes, customers] = await Promise.all([
            this.orm.searchRead("deployfleet.depot", [], ["name"], { order: "name asc" }),
            this.orm.searchRead("deployfleet.vehicle.type", [], ["name"], { order: "name asc" }),
            this.orm.searchRead("res.partner", [["customer_rank", ">", 0]], ["name"], { order: "name asc", limit: 200 }),
        ]);
        this.state.depots = depots;
        this.state.vehicleTypes = vehicleTypes;
        this.state.customers = customers;
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "active"
                    ? this.state.shipments.filter((s) => s.state !== "delivered" && s.state !== "cancelled").length
                    : this.state.shipments.filter((s) => s.state === filter.key).length,
        }));
    }

    get filteredShipments() {
        if (this.state.stateFilter === "active") {
            return this.state.shipments.filter((s) => s.state !== "delivered" && s.state !== "cancelled");
        }
        return this.state.shipments.filter((s) => s.state === this.state.stateFilter);
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    isCancellable(state) {
        return CANCELLABLE_STATES.has(state);
    }

    async onSelectShipment(shipmentId, state) {
        if (this.state.selectedShipmentId === shipmentId) {
            this.state.selectedShipmentId = null;
            this.copilotContext.clearContext();
            return;
        }
        this.state.selectedShipmentId = shipmentId;
        const shipmentForContext = this.state.shipments.find((s) => s.id === shipmentId);
        this.copilotContext.setContext({
            domain: "dispatch",
            model: "deployfleet.shipment",
            recordId: shipmentId,
            recordLabel: shipmentForContext?.name || `Shipment #${shipmentId}`,
        });
        if (state === "confirmed" && !this.state.candidatesByShipment[shipmentId]) {
            await this.loadCandidates(shipmentId);
        }
        if (
            ["assigned", "in_transit", "delivered"].includes(state) &&
            !this.state.assignmentInfoByShipment[shipmentId]
        ) {
            await this.loadAssignmentInfo(shipmentId);
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

    async loadAssignmentInfo(shipmentId) {
        const assignments = await this.orm.searchRead(
            "deployfleet.dispatch.assignment",
            [["shipment_id", "=", shipmentId], ["state", "=", "confirmed"]],
            ["driver_id", "vehicle_id", "planned_departure"],
            { limit: 1 },
        );
        this.state.assignmentInfoByShipment[shipmentId] = assignments[0] || null;
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

    async onShipmentAction(shipmentId, method) {
        this.state.actingShipmentId = shipmentId;
        try {
            await this.orm.call("deployfleet.shipment", method, [[shipmentId]]);
            await this.loadShipments();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingShipmentId = null;
        }
    }

    onNewShipmentInput(field, value) {
        this.state.newShipment[field] = value;
    }

    async onCreateShipment() {
        const { customer_id, pickup_depot_id, dropoff_depot_id, requested_pickup_date,
            cargo_description, weight_kg, required_vehicle_type_id } = this.state.newShipment;
        if (!customer_id || !pickup_depot_id || !dropoff_depot_id) {
            this.notification.add("Customer, pickup, and drop-off depot are required.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.shipment", [
                {
                    customer_id: parseInt(customer_id, 10),
                    pickup_depot_id: parseInt(pickup_depot_id, 10),
                    dropoff_depot_id: parseInt(dropoff_depot_id, 10),
                    requested_pickup_date: toOdooDatetime(requested_pickup_date),
                    cargo_description: cargo_description || false,
                    weight_kg: weight_kg ? parseFloat(weight_kg) : 0,
                    required_vehicle_type_id: required_vehicle_type_id ? parseInt(required_vehicle_type_id, 10) : false,
                },
            ]);
            this.state.newShipment = {
                customer_id: "", pickup_depot_id: "", dropoff_depot_id: "",
                requested_pickup_date: "", cargo_description: "", weight_kg: "", required_vehicle_type_id: "",
            };
            await this.loadShipments();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
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
