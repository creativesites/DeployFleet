/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const LOG_FILTERS = [
    { key: "all", label: "All" },
    { key: "anomalous", label: "Anomalies" },
];

const LOG_LIMIT = 200;

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Fuel Intelligence (Fleet & Vehicles domain, doc 20 gap #3) — a
 * fleet-wide fuel view, replacing the stock `deployfleet.fuel.log`
 * list/form, which today can only be browsed one vehicle at a time
 * (Vehicle 360 shows the last 5 logs per vehicle; the stock list has
 * no anomaly-first sorting or fleet-wide anomaly count).
 *
 * Reconciles the same two independent fuel-anomaly signals Vehicle 360
 * already reconciles per-vehicle (doc 16 §7.10) — `fuel.log.is_anomaly`
 * (flat 30%-above-trailing-average threshold) and the separate,
 * stricter `deployfleet.fuel.anomaly` z-score model — but fleet-wide
 * here: a log is flagged if either signal fires, showing the z-score
 * when the AI model has scored it. The most recent `LOG_LIMIT` logs
 * across the whole fleet are loaded, newest first, filterable to
 * Anomalies only.
 *
 * Includes a real "Log Fuel" quick-add form (vehicle/driver/date/
 * odometer/liters/cost), wired to a plain `orm.create` — the one
 * genuine record-level gap the stock list/form covered but no custom
 * screen did yet. Registry-ledger visual language, same as Parts/Asset
 * Registries and the Vehicle Types Workspace.
 *
 * Soft-coupling: `deployfleet.fuel.log`/`deployfleet.fuel.anomaly` are
 * referenced as plain runtime strings, the same decision made
 * throughout `deployfleet_ui`.
 */
export class DeployfleetFuelIntelligence extends Component {
    static template = "deployfleet_ui.FuelIntelligence";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            logs: [],
            logFilter: "all",
            vehicles: [],
            drivers: [],
            newLog: { vehicle_id: "", driver_id: "", date: "", odometer: "", liters: "", total_cost: "" },
            creating: false,
        });

        onWillStart(() => this.loadAll());
    }

    get logFilters() {
        return LOG_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.logs.length
                    : this.state.logs.filter((log) => log.isAnomalous).length,
        }));
    }

    get filteredLogs() {
        if (this.state.logFilter === "anomalous") {
            return this.state.logs.filter((log) => log.isAnomalous);
        }
        return this.state.logs;
    }

    async loadAll() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const [logs, vehicles, drivers] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.fuel.log",
                    [],
                    ["vehicle_id", "driver_id", "date", "liters", "total_cost", "consumption_l_per_100km", "is_anomaly"],
                    { order: "date desc, id desc", limit: LOG_LIMIT },
                ),
                this.orm.searchRead("deployfleet.vehicle", [["status", "!=", "retired"]], ["license_plate", "name"], {
                    order: "license_plate asc",
                }),
                this.orm.searchRead("hr.employee", [["deployfleet_is_driver", "=", true]], ["name"], {
                    order: "name asc",
                }),
            ]);

            const logIds = logs.map((log) => log.id);
            let zScoreByLogId = {};
            if (logIds.length) {
                const anomalies = await this.orm.searchRead(
                    "deployfleet.fuel.anomaly",
                    [["fuel_log_id", "in", logIds]],
                    ["fuel_log_id", "z_score"],
                );
                zScoreByLogId = Object.fromEntries(anomalies.map((a) => [a.fuel_log_id[0], a.z_score]));
            }

            this.state.logs = logs.map((log) => ({
                ...log,
                anomalyZScore: zScoreByLogId[log.id] ?? null,
                isAnomalous: log.is_anomaly || log.id in zScoreByLogId,
            }));
            this.state.vehicles = vehicles;
            this.state.drivers = drivers;
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    fuelAnomalyLabel(log) {
        return log.anomalyZScore !== null ? `Anomaly (z=${log.anomalyZScore.toFixed(1)})` : "Anomaly";
    }

    onNewLogFieldInput(field, value) {
        this.state.newLog[field] = value;
    }

    async onLogFuel() {
        const { vehicle_id, driver_id, date, odometer, liters, total_cost } = this.state.newLog;
        if (!vehicle_id || !date || !odometer || !liters) {
            this.notification.add("Vehicle, date, odometer, and liters are required.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.fuel.log", [
                {
                    vehicle_id: parseInt(vehicle_id, 10),
                    driver_id: driver_id ? parseInt(driver_id, 10) : false,
                    date,
                    odometer: parseFloat(odometer),
                    liters: parseFloat(liters),
                    total_cost: total_cost ? parseFloat(total_cost) : 0,
                },
            ]);
            this.state.newLog = { vehicle_id: "", driver_id: "", date: "", odometer: "", liters: "", total_cost: "" };
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.fuel_intelligence", DeployfleetFuelIntelligence);
