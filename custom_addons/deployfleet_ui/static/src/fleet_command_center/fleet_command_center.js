/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";

const STATUS_FILTERS = [
    { key: "all", label: "All" },
    { key: "available", label: "Available" },
    { key: "assigned", label: "Assigned" },
    { key: "maintenance", label: "Maintenance" },
    { key: "breakdown", label: "Breakdown" },
];

// Status -> StatusBadge semantic, per doc 17 §2.2 (never a bare re-use of
// Odoo's own selection-field color, always mapped deliberately).
const STATUS_BADGE_VARIANT = {
    available: "success",
    assigned: "info",
    maintenance: "warning",
    breakdown: "danger",
    retired: "info",
};

const STATUS_LABEL = {
    available: "Available",
    assigned: "Assigned",
    maintenance: "Maintenance",
    breakdown: "Breakdown",
    retired: "Retired",
};

const DOCUMENT_STATE_LABEL = {
    valid: "Valid",
    expiring_soon: "Expiring Soon",
    expired: "Expired",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Fleet Command Center (doc 16 §3.7/§7.10, Phase C / Slice 3) — the fleet
 * manager's consolidated view: every vehicle's status, current
 * assignment, compliance, maintenance, and recent fuel history in one
 * screen instead of four separate module list views.
 *
 * **Scope note relative to doc 16 §7.10's original description**, same
 * transparency discipline as the Dispatch Board (§7.9): doc 16 describes
 * a sidebar + tabbed table + row-click **slide-in inspector**. There is
 * no Drawer/Inspector component yet (doc 18's catalog still lists it as
 * not built) and no signature "wow" widgets yet either (Truck Health
 * Ring, Profit Waterfall — both explicitly "Aspirational" in doc 18).
 * This slice ships the real, working substance — a genuine per-vehicle
 * consolidated read across `deployfleet.compliance.document`,
 * `deployfleet.fuel.log`, `deployfleet.maintenance.schedule`, and
 * `deployfleet.trip` — via the same tap-to-expand accordion pattern the
 * Dispatch Board already established, rather than inventing a one-off
 * slide-in panel ahead of a real Drawer component existing. Quick
 * status-transition actions (available/maintenance/breakdown) are wired
 * to the vehicle's real `action_set_*` methods, so this is a genuinely
 * actionable screen, not read-only.
 *
 * Soft-coupling: deployfleet.vehicle/compliance.document/fuel.log/
 * maintenance.schedule/trip are referenced as plain runtime strings, the
 * same decision already made throughout deployfleet_ui.
 */
export class DeployfleetFleetCommandCenter extends Component {
    static template = "deployfleet_ui.FleetCommandCenter";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetMetricCard };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            vehicles: [],
            detailByVehicleId: {},
            selectedVehicleId: null,
            statusFilter: "all",
            transitioningVehicleId: null,
        });

        onWillStart(() => this.loadVehicles());
    }

    get statusFilters() {
        return STATUS_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.vehicles.length
                    : this.state.vehicles.filter((vehicle) => vehicle.status === filter.key).length,
        }));
    }

    get filteredVehicles() {
        if (this.state.statusFilter === "all") {
            return this.state.vehicles;
        }
        return this.state.vehicles.filter((vehicle) => vehicle.status === this.state.statusFilter);
    }

    statusBadgeVariant(status) {
        return STATUS_BADGE_VARIANT[status] || "info";
    }

    statusLabel(status) {
        return STATUS_LABEL[status] || status;
    }

    documentStateLabel(state) {
        return DOCUMENT_STATE_LABEL[state] || state;
    }

    async loadVehicles() {
        this.state.loading = true;
        const vehicles = await this.orm.searchRead(
            "deployfleet.vehicle",
            [["status", "!=", "retired"]],
            ["license_plate", "name", "status", "vehicle_type_id", "current_driver_id", "current_trip_id"],
            { order: "license_plate asc" },
        );
        this.state.vehicles = vehicles;
        this.state.loading = false;
    }

    async onSelectVehicle(vehicleId) {
        if (this.state.selectedVehicleId === vehicleId) {
            this.state.selectedVehicleId = null;
            return;
        }
        this.state.selectedVehicleId = vehicleId;
        if (!this.state.detailByVehicleId[vehicleId]) {
            await this.loadVehicleDetail(vehicleId);
        }
    }

    async loadVehicleDetail(vehicleId) {
        const [documents, fuelLogs, maintenanceSchedules] = await Promise.all([
            this.orm.searchRead(
                "deployfleet.compliance.document",
                [["res_model", "=", "deployfleet.vehicle"], ["res_id", "=", vehicleId]],
                ["document_type_id", "expiry_date", "state"],
                { order: "expiry_date asc" },
            ),
            this.orm.searchRead(
                "deployfleet.fuel.log",
                [["vehicle_id", "=", vehicleId]],
                ["date", "liters", "total_cost", "consumption_l_per_100km", "is_anomaly"],
                { order: "date desc", limit: 5 },
            ),
            this.orm.searchRead(
                "deployfleet.maintenance.schedule",
                [["vehicle_id", "=", vehicleId]],
                ["name", "is_due", "next_due_date", "next_due_odometer"],
                { order: "is_due desc" },
            ),
        ]);

        let trip = null;
        const vehicle = this.state.vehicles.find((v) => v.id === vehicleId);
        if (vehicle?.current_trip_id) {
            const trips = await this.orm.searchRead(
                "deployfleet.trip",
                [["id", "=", vehicle.current_trip_id[0]]],
                ["name", "state", "route_id", "planned_departure", "planned_arrival"],
            );
            trip = trips[0] || null;
        }

        this.state.detailByVehicleId[vehicleId] = { documents, fuelLogs, maintenanceSchedules, trip };
    }

    async onSetStatus(vehicleId, actionMethod) {
        this.state.transitioningVehicleId = vehicleId;
        try {
            await this.orm.call("deployfleet.vehicle", actionMethod, [[vehicleId]]);
            await this.loadVehicles();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.transitioningVehicleId = null;
        }
    }

    onOpenVehicleForm(vehicleId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.vehicle",
            res_id: vehicleId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.fleet_command_center", DeployfleetFleetCommandCenter);
