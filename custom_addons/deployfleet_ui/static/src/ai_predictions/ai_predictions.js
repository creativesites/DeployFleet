/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const TABS = [
    { key: "maintenance", label: "Maintenance Risk" },
    { key: "fuel", label: "Fuel Anomalies" },
];

const RISK_FILTERS = [
    { key: "all", label: "All" },
    { key: "high", label: "High" },
    { key: "medium", label: "Medium" },
    { key: "low", label: "Low" },
];

const RISK_BADGE_VARIANT = { high: "danger", medium: "warning", low: "success" };
const RISK_LABEL = { high: "High", medium: "Medium", low: "Low" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * AI Predictions (AI & Intelligence domain) — a fleet-wide browsing
 * screen over `deployfleet.maintenance.prediction` and
 * `deployfleet.fuel.anomaly`, built per the user's explicit choice
 * during this domain's design conversation (both signals are already
 * surfaced inline elsewhere — `AiRecommendationCard` on Fleet Command
 * Center/Maintenance Planner for predictions, a reconciled read inside
 * Fuel Intelligence for anomalies — but the user wanted a dedicated
 * fleet-wide view on top of that rather than treating those as
 * sufficient, the same way Driver Availability was instead judged
 * "closed by an existing screen" in the Dispatch & Trips domain).
 *
 * Two tabs, since the two models have genuinely different shapes
 * (confirmed by source read: risk_score/risk_level/basis vs. a bare
 * z_score) rather than one merged list pretending they're the same
 * kind of row. Both models are AI-computed, read-only data (populated
 * by their own daily crons) — this screen has no create/edit form,
 * only a per-vehicle "Open Vehicle" escape hatch to the stock form,
 * the same "no per-record params plumbing on an unverified action-
 * manager API" caution that already ruled out a params-based Vehicle
 * Profile screen in Fleet & Vehicles.
 *
 * Soft-coupling: `deployfleet.maintenance.prediction`/
 * `deployfleet.fuel.anomaly`/`deployfleet.fuel.log` are referenced as
 * plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetAiPredictions extends Component {
    static template = "deployfleet_ui.AiPredictions";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.tabs = TABS;
        this.state = useState({
            loading: true,
            activeTab: "maintenance",
            predictions: [],
            anomalies: [],
            riskFilter: "all",
            selectedPredictionId: null,
            selectedAnomalyId: null,
            fuelLogById: {},
        });

        onWillStart(() => this.loadAllInitialData());
    }

    async loadAllInitialData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await Promise.all([this.loadPredictions(), this.loadAnomalies()]);
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async loadPredictions() {
        this.state.predictions = await this.orm.searchRead(
            "deployfleet.maintenance.prediction",
            [],
            [
                "vehicle_id", "computed_date", "consumption_trend_slope",
                "recent_job_card_count", "risk_score", "risk_level", "basis",
            ],
            { order: "risk_score desc" },
        );
    }

    async loadAnomalies() {
        this.state.anomalies = await this.orm.searchRead(
            "deployfleet.fuel.anomaly",
            [],
            ["fuel_log_id", "vehicle_id", "z_score", "detected_date"],
            { order: "z_score desc" },
        );
    }

    onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
    }

    get riskFilters() {
        return RISK_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.predictions.length
                    : this.state.predictions.filter((p) => p.risk_level === filter.key).length,
        }));
    }

    get filteredPredictions() {
        if (this.state.riskFilter === "all") {
            return this.state.predictions;
        }
        return this.state.predictions.filter((p) => p.risk_level === this.state.riskFilter);
    }

    riskLabel(level) {
        return RISK_LABEL[level] || level;
    }

    riskBadgeVariant(level) {
        return RISK_BADGE_VARIANT[level] || "info";
    }

    onSelectPrediction(predictionId) {
        this.state.selectedPredictionId = this.state.selectedPredictionId === predictionId ? null : predictionId;
    }

    async onSelectAnomaly(anomalyId, fuelLogId) {
        if (this.state.selectedAnomalyId === anomalyId) {
            this.state.selectedAnomalyId = null;
            return;
        }
        this.state.selectedAnomalyId = anomalyId;
        if (!this.state.fuelLogById[fuelLogId]) {
            try {
                const [log] = await this.orm.read(
                    "deployfleet.fuel.log", [fuelLogId],
                    ["date", "liters", "total_cost", "consumption_l_per_100km"],
                );
                this.state.fuelLogById[fuelLogId] = log;
            } catch (error) {
                this.notification.add(extractErrorMessage(error), { type: "danger" });
            }
        }
    }

    onOpenVehicle(vehicleId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.vehicle",
            res_id: vehicleId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.ai_predictions", DeployfleetAiPredictions);
