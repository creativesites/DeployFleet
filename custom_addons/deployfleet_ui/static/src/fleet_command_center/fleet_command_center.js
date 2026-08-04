/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";
import { DeployfleetAiRecommendationCard } from "../components/ai_recommendation_card/ai_recommendation_card";
import { useCopilotContext } from "../copilot_rail/copilot_context";

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

const TYRE_POSITION_LABEL = {
    front_left: "Front Left",
    front_right: "Front Right",
    rear_left_outer: "Rear Left Outer",
    rear_left_inner: "Rear Left Inner",
    rear_right_outer: "Rear Right Outer",
    rear_right_inner: "Rear Right Inner",
    spare: "Spare",
};

const TYRE_STATE_LABEL = {
    fitted: "Fitted",
    retreaded: "Retreaded",
    scrapped: "Scrapped",
};

const JOB_CARD_STATE_LABEL = {
    open: "Open",
    diagnosis: "Diagnosis",
    repair: "Repair",
    approval: "Pending Approval",
    closed: "Closed",
};

const JOB_CARD_STATE_BADGE_VARIANT = {
    open: "info",
    diagnosis: "info",
    repair: "warning",
    approval: "warning",
    closed: "success",
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
 * maintenance.schedule/trip/maintenance.prediction are referenced as
 * plain runtime strings, the same decision already made throughout
 * deployfleet_ui.
 *
 * **Phase D addition:** the expanded detail also surfaces the vehicle's
 * latest `deployfleet.maintenance.prediction` (Phase 5's real predictive-
 * maintenance model — a closed-form risk score from fuel-consumption
 * trend + recent workshop job cards, not a placeholder) as an
 * `AiRecommendationCard`, doc 16 §7.9/§8's "ambient AI on this screen"
 * concept made concrete for the first time anywhere in `deployfleet_ui`.
 * Silent when `risk_level` is "low", the same silent-unless-actionable
 * discipline as Mission Control's attention strip — a card for every
 * vehicle regardless of risk would be noise, not signal.
 *
 * **Vehicle Profile addition (doc 20 gap #1, Fleet & Vehicles
 * custom-views work):** the expanded detail now also has a real,
 * editable "Identity & Capacity" section — `deployfleet.vehicle`'s
 * stock form had zero tabs and zero related-record rollups (confirmed
 * by source read before designing, doc 20 §6), so rather than build a
 * second, separate "Vehicle Profile" screen with its own unverified
 * per-record action-params plumbing, this screen's already-working
 * expanded card was evolved into the vehicle's actual profile page:
 * license plate, model, vehicle type, current driver, and odometer
 * (all delegated `fleet.vehicle` or `deployfleet.vehicle` fields) plus
 * the four editable capacity fields, saved via a plain `orm.write`.
 * `payload_capacity_kg` stays read-only in the summary line — it's a
 * stored compute (`gross_vehicle_weight_kg` − `tare_weight_kg`), not a
 * field a user sets directly. "Open full record" remains as a fallback
 * for any stock-form field this section doesn't yet cover.
 */
export class DeployfleetFleetCommandCenter extends Component {
    static template = "deployfleet_ui.FleetCommandCenter";
    static components = {
        DeployfleetButton,
        DeployfleetStatusBadge,
        DeployfleetStatusPill,
        DeployfleetMetricCard,
        DeployfleetAiRecommendationCard,
    };
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
            vehicles: [],
            detailByVehicleId: {},
            selectedVehicleId: null,
            statusFilter: "all",
            transitioningVehicleId: null,
            vehicleTypes: [],
            driverOptions: [],
            vehicleModels: [],
            editByVehicleId: {},
            savingVehicleId: null,
        });

        onWillStart(() => Promise.all([this.loadVehicles(), this.loadEditOptions()]));
    }

    async loadEditOptions() {
        const [vehicleTypes, driverOptions, vehicleModels] = await Promise.all([
            this.orm.searchRead("deployfleet.vehicle.type", [], ["name"], { order: "sequence asc" }),
            this.orm.searchRead("hr.employee", [["deployfleet_is_driver", "=", true]], ["name"], {
                order: "name asc",
            }),
            this.orm.searchRead("fleet.vehicle.model", [], ["name"], { order: "name asc", limit: 200 }),
        ]);
        this.state.vehicleTypes = vehicleTypes;
        this.state.driverOptions = driverOptions;
        this.state.vehicleModels = vehicleModels;
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

    tyrePositionLabel(position) {
        return TYRE_POSITION_LABEL[position] || position;
    }

    tyreStateLabel(state) {
        return TYRE_STATE_LABEL[state] || state;
    }

    jobCardStateLabel(state) {
        return JOB_CARD_STATE_LABEL[state] || state;
    }

    jobCardStateBadgeVariant(state) {
        return JOB_CARD_STATE_BADGE_VARIANT[state] || "info";
    }

    fuelAnomalyLabel(log) {
        return log.anomalyZScore !== null ? `Anomaly (z=${log.anomalyZScore.toFixed(1)})` : "Anomaly";
    }

    predictionTitle(prediction) {
        const levelLabel = prediction.risk_level === "high" ? "High" : "Medium";
        return `${levelLabel} predicted maintenance risk`;
    }

    predictionMeta(prediction) {
        return `Risk score: ${prediction.risk_score}/100`;
    }

    async loadVehicles() {
        this.state.loading = true;
        const vehicles = await this.orm.searchRead(
            "deployfleet.vehicle",
            [["status", "!=", "retired"]],
            [
                "license_plate",
                "name",
                "status",
                "vehicle_type_id",
                "current_driver_id",
                "current_trip_id",
                "model_id",
                "odometer",
                "max_weight_kg",
                "max_volume_m3",
                "gross_vehicle_weight_kg",
                "tare_weight_kg",
                "payload_capacity_kg",
            ],
            { order: "license_plate asc" },
        );
        this.state.vehicles = vehicles;
        this.state.loading = false;
    }

    async onSelectVehicle(vehicleId) {
        if (this.state.selectedVehicleId === vehicleId) {
            this.state.selectedVehicleId = null;
            this.copilotContext.clearContext();
            return;
        }
        this.state.selectedVehicleId = vehicleId;
        const vehicleForContext = this.state.vehicles.find((v) => v.id === vehicleId);
        this.copilotContext.setContext({
            domain: "fleet",
            model: "deployfleet.vehicle",
            recordId: vehicleId,
            recordLabel: vehicleForContext?.license_plate || vehicleForContext?.display_name || `Vehicle #${vehicleId}`,
        });
        if (!this.state.editByVehicleId[vehicleId]) {
            const vehicle = this.state.vehicles.find((v) => v.id === vehicleId);
            this.state.editByVehicleId[vehicleId] = {
                license_plate: vehicle.license_plate || "",
                model_id: vehicle.model_id ? vehicle.model_id[0] : "",
                vehicle_type_id: vehicle.vehicle_type_id ? vehicle.vehicle_type_id[0] : "",
                current_driver_id: vehicle.current_driver_id ? vehicle.current_driver_id[0] : "",
                odometer: vehicle.odometer,
                max_weight_kg: vehicle.max_weight_kg,
                max_volume_m3: vehicle.max_volume_m3,
                gross_vehicle_weight_kg: vehicle.gross_vehicle_weight_kg,
                tare_weight_kg: vehicle.tare_weight_kg,
            };
        }
        if (!this.state.detailByVehicleId[vehicleId]) {
            await this.loadVehicleDetail(vehicleId);
        }
    }

    onEditFieldInput(vehicleId, field, value) {
        this.state.editByVehicleId[vehicleId][field] = value;
    }

    async onSaveVehicleProfile(vehicleId) {
        const edit = this.state.editByVehicleId[vehicleId];
        if (!edit.license_plate || !edit.license_plate.trim()) {
            this.notification.add("License plate is required.", { type: "danger" });
            return;
        }
        this.state.savingVehicleId = vehicleId;
        try {
            await this.orm.write("deployfleet.vehicle", [vehicleId], {
                license_plate: edit.license_plate.trim(),
                model_id: edit.model_id ? parseInt(edit.model_id, 10) : false,
                vehicle_type_id: edit.vehicle_type_id ? parseInt(edit.vehicle_type_id, 10) : false,
                current_driver_id: edit.current_driver_id ? parseInt(edit.current_driver_id, 10) : false,
                odometer: parseFloat(edit.odometer) || 0,
                max_weight_kg: parseFloat(edit.max_weight_kg) || 0,
                max_volume_m3: parseFloat(edit.max_volume_m3) || 0,
                gross_vehicle_weight_kg: parseFloat(edit.gross_vehicle_weight_kg) || 0,
                tare_weight_kg: parseFloat(edit.tare_weight_kg) || 0,
            });
            delete this.state.editByVehicleId[vehicleId];
            await this.loadVehicles();
            this.notification.add("Vehicle profile updated.", { type: "success" });
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingVehicleId = null;
        }
    }

    async loadVehicleDetail(vehicleId) {
        const [documents, fuelLogs, maintenanceSchedules, predictions, tyres, insurancePolicies, jobCards] =
            await Promise.all([
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
                this.orm.searchRead(
                    "deployfleet.maintenance.prediction",
                    [["vehicle_id", "=", vehicleId]],
                    ["risk_score", "risk_level", "basis", "computed_date"],
                    { order: "computed_date desc", limit: 1 },
                ),
                // Vehicle 360 (Fleet & Vehicles custom-views initiative):
                // non-scrapped tyres, the vehicle's most recent insurance
                // policy, and open (non-closed) workshop job cards — per
                // the "Tyres/Insurance/Parts-and-Workshop-summary fold
                // into Vehicle 360" decision (CLAUDE.md §10). Parts itself
                // has no vehicle_id (confirmed by source read), so it
                // stays its own registry screen rather than appearing here.
                this.orm.searchRead(
                    "deployfleet.tyre",
                    [["vehicle_id", "=", vehicleId], ["state", "!=", "scrapped"]],
                    ["position", "state", "tread_depth_mm"],
                    { order: "position asc" },
                ),
                this.orm.searchRead(
                    "deployfleet.insurance.policy",
                    [["vehicle_id", "=", vehicleId]],
                    ["policy_number", "insurer_id", "end_date", "premium_amount"],
                    { order: "end_date desc", limit: 1 },
                ),
                this.orm.searchRead(
                    "deployfleet.workshop.job.card",
                    [["vehicle_id", "=", vehicleId], ["state", "!=", "closed"]],
                    ["name", "state", "total_cost", "opened_date"],
                    { order: "opened_date desc" },
                ),
            ]);

        // Reconcile the two independent fuel-anomaly signals into one
        // indicator per the agreed decision (CLAUDE.md §10): fuel.log's
        // own is_anomaly is a flat 30%-above-trailing-average threshold;
        // deployfleet.fuel.anomaly is a separate, stricter z-score signal
        // (>=2.0, needs 3+ prior logs) from the Phase 5 AI layer. A log is
        // flagged anomalous if either signal fires; the z-score, being
        // the more precise number, is shown when available.
        const fuelLogIds = fuelLogs.map((log) => log.id);
        let zScoreByLogId = {};
        if (fuelLogIds.length) {
            const anomalies = await this.orm.searchRead(
                "deployfleet.fuel.anomaly",
                [["fuel_log_id", "in", fuelLogIds]],
                ["fuel_log_id", "z_score"],
            );
            zScoreByLogId = Object.fromEntries(anomalies.map((a) => [a.fuel_log_id[0], a.z_score]));
        }
        const reconciledFuelLogs = fuelLogs.map((log) => ({
            ...log,
            anomalyZScore: zScoreByLogId[log.id] ?? null,
            isAnomalous: log.is_anomaly || log.id in zScoreByLogId,
        }));

        let insurance = insurancePolicies[0] || null;
        if (insurance) {
            const openClaimsCount = await this.orm.searchCount("deployfleet.insurance.claim", [
                ["policy_id", "=", insurance.id],
                ["state", "not in", ["paid", "rejected"]],
            ]);
            insurance = { ...insurance, openClaimsCount };
        }

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

        const latestPrediction = predictions[0] || null;
        const prediction = latestPrediction && latestPrediction.risk_level !== "low" ? latestPrediction : null;

        this.state.detailByVehicleId[vehicleId] = {
            documents,
            fuelLogs: reconciledFuelLogs,
            maintenanceSchedules,
            trip,
            prediction,
            tyres,
            insurance,
            jobCards,
        };
    }

    onDismissPrediction(vehicleId) {
        const detail = this.state.detailByVehicleId[vehicleId];
        if (detail) {
            detail.prediction = null;
        }
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
