/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const STATE_FILTERS = [
    { key: "active", label: "Active" },
    { key: "fitted", label: "Fitted" },
    { key: "retreaded", label: "Retreaded" },
    { key: "scrapped", label: "Scrapped" },
    { key: "all", label: "All" },
];

const TYRE_POSITIONS = [
    ["front_left", "Front Left"],
    ["front_right", "Front Right"],
    ["rear_left_outer", "Rear Left Outer"],
    ["rear_left_inner", "Rear Left Inner"],
    ["rear_right_outer", "Rear Right Outer"],
    ["rear_right_inner", "Rear Right Inner"],
    ["spare", "Spare"],
];

const TYRE_POSITION_LABEL = Object.fromEntries(TYRE_POSITIONS);

const STATE_LABEL = { fitted: "Fitted", retreaded: "Retreaded", scrapped: "Scrapped" };
const STATE_BADGE_VARIANT = { fitted: "success", retreaded: "warning", scrapped: "info" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Tyre Manager (Fleet & Vehicles domain, doc 20 gap #4) — a fleet-wide
 * tyre view, replacing the two ways tyres were previously reachable: a
 * stock list/form under `deployfleet_parts`'s menu, or read-only inside
 * one vehicle's Vehicle 360 detail (doc 16 §7.10). Neither gave a
 * fleet-wide "which tyres need attention" view — the actual workflow a
 * workshop supervisor needs when planning a batch replacement.
 *
 * Filter chips by state, defaulting to "Active" (fitted + retreaded,
 * excluding scrapped — mirrors the Fleet Command Center/Workshop
 * Board's "exclude the terminal state by default" pattern), ordered
 * worst-tread-first so the tyres most worth attention surface without
 * a manual sort (the same "so what" discipline as Driver Scorecards).
 * Tap-to-expand reveals the tread-depth-reading history, rotation/
 * retread/scrap event history, and three real actions wired to the
 * tyre's actual backend methods: `action_record_reading(tread_depth_mm,
 * odometer)`, `action_rotate(new_position)`, `action_retread()`,
 * `action_scrap()`.
 *
 * **Real backend ACL gap found and fixed alongside this screen:**
 * `deployfleet.tyre.event` denied dispatcher `create` even though
 * dispatcher already has `write` on the parent `deployfleet.tyre`
 * model — but `action_rotate`/`action_retread`/`action_scrap` all
 * internally create a `deployfleet.tyre.event` record as part of the
 * same transaction, so those actions would have raised an AccessError
 * for the dispatcher role despite the tyre-level ACL implying dispatcher
 * should be able to perform them (the same operational authority
 * dispatcher already has for vehicle status transitions). Fixed by
 * granting dispatcher `create` (not `write` — events are an
 * append-only history, never edited after creation) on
 * `deployfleet.tyre.event`, in `deployfleet_tyres/security/
 * ir.model.access.csv`.
 *
 * Soft-coupling: `deployfleet.tyre`/`deployfleet.tyre.reading`/
 * `deployfleet.tyre.event` are referenced as plain runtime strings,
 * the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetTyreManager extends Component {
    static template = "deployfleet_ui.TyreManager";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            tyres: [],
            stateFilter: "active",
            selectedTyreId: null,
            detailByTyreId: {},
            newReadingByTyreId: {},
            rotateTargetByTyreId: {},
            actingTyreId: null,
        });
        this.tyrePositions = TYRE_POSITIONS;

        onWillStart(() => this.loadTyres());
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.tyres.length
                    : filter.key === "active"
                    ? this.state.tyres.filter((t) => t.state !== "scrapped").length
                    : this.state.tyres.filter((t) => t.state === filter.key).length,
        }));
    }

    get filteredTyres() {
        if (this.state.stateFilter === "all") {
            return this.state.tyres;
        }
        if (this.state.stateFilter === "active") {
            return this.state.tyres.filter((t) => t.state !== "scrapped");
        }
        return this.state.tyres.filter((t) => t.state === this.state.stateFilter);
    }

    positionLabel(position) {
        return TYRE_POSITION_LABEL[position] || position;
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    async loadTyres() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const tyres = await this.orm.searchRead(
                "deployfleet.tyre",
                [],
                ["vehicle_id", "position", "serial_number", "tread_depth_mm", "state"],
                {},
            );
            tyres.sort((a, b) => a.tread_depth_mm - b.tread_depth_mm);
            this.state.tyres = tyres;
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectTyre(tyreId) {
        if (this.state.selectedTyreId === tyreId) {
            this.state.selectedTyreId = null;
            return;
        }
        this.state.selectedTyreId = tyreId;
        if (!this.state.detailByTyreId[tyreId]) {
            const [readings, events] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.tyre.reading",
                    [["tyre_id", "=", tyreId]],
                    ["date", "tread_depth_mm", "odometer"],
                    { order: "date desc", limit: 10 },
                ),
                this.orm.searchRead(
                    "deployfleet.tyre.event",
                    [["tyre_id", "=", tyreId]],
                    ["date", "event_type", "from_position", "to_position"],
                    { order: "date desc", limit: 10 },
                ),
            ]);
            this.state.detailByTyreId[tyreId] = { readings, events };
        }
    }

    onNewReadingInput(tyreId, field, value) {
        this.state.newReadingByTyreId[tyreId] = { ...this.state.newReadingByTyreId[tyreId], [field]: value };
    }

    async onRecordReading(tyreId) {
        const reading = this.state.newReadingByTyreId[tyreId] || {};
        const treadDepth = parseFloat(reading.tread_depth_mm);
        if (Number.isNaN(treadDepth) || treadDepth < 0) {
            this.notification.add("Enter a valid tread depth.", { type: "danger" });
            return;
        }
        this.state.actingTyreId = tyreId;
        try {
            await this.orm.call("deployfleet.tyre", "action_record_reading", [
                [tyreId],
                treadDepth,
                reading.odometer ? parseFloat(reading.odometer) : null,
            ]);
            this.state.newReadingByTyreId[tyreId] = {};
            delete this.state.detailByTyreId[tyreId];
            await this.loadTyres();
            await this.onSelectTyre(tyreId);
            this.state.selectedTyreId = tyreId;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTyreId = null;
        }
    }

    onRotateTargetInput(tyreId, value) {
        this.state.rotateTargetByTyreId[tyreId] = value;
    }

    async onRotate(tyreId) {
        const target = this.state.rotateTargetByTyreId[tyreId];
        if (!target) {
            this.notification.add("Choose a position to rotate to.", { type: "danger" });
            return;
        }
        await this.runAction(tyreId, "action_rotate", [target]);
    }

    async onRetread(tyreId) {
        await this.runAction(tyreId, "action_retread", []);
    }

    async onScrap(tyreId) {
        await this.runAction(tyreId, "action_scrap", []);
    }

    async runAction(tyreId, method, extraArgs) {
        this.state.actingTyreId = tyreId;
        try {
            await this.orm.call("deployfleet.tyre", method, [[tyreId], ...extraArgs]);
            delete this.state.detailByTyreId[tyreId];
            await this.loadTyres();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTyreId = null;
        }
    }
}

registry.category("actions").add("deployfleet_ui.tyre_manager", DeployfleetTyreManager);
