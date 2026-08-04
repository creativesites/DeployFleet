/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const SCORE_FILTERS = [
    { key: "all", label: "All" },
    { key: "good", label: "Good (80+)" },
    { key: "watch", label: "Watch (50-79)" },
    { key: "at_risk", label: "At Risk (<50)" },
];

const SCORE_BAND_VARIANT = {
    good: "success",
    watch: "warning",
    at_risk: "danger",
};

const EVENT_TYPE_LABEL = {
    accident: "Accident",
    violation: "Traffic Violation",
    harsh_braking: "Harsh Braking",
    speeding: "Speeding",
    fuel_abuse: "Fuel Abuse Pattern",
    late_delivery: "Late Delivery",
    other: "Other",
};

const LICENSE_CLASS_OPTIONS = [
    ["b", "Class B — Light Vehicle"],
    ["c1", "Class C1 — Medium Goods"],
    ["c", "Class C — Heavy Goods"],
    ["d1", "Class D1 — Minibus"],
    ["d", "Class D — Bus"],
    ["ce", "Class CE — Articulated / Trailer Combination"],
];

const LICENSE_CLASS_LABEL = Object.fromEntries(LICENSE_CLASS_OPTIONS);

const ADVANCE_STATE_LABEL = { issued: "Issued", reconciled: "Reconciled", deducted: "Deducted" };
const ADVANCE_STATE_BADGE_VARIANT = { issued: "info", reconciled: "warning", deducted: "success" };

const LEAVE_STATE_LABEL = {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    rejected: "Rejected",
    cancelled: "Cancelled",
};
const LEAVE_STATE_BADGE_VARIANT = {
    draft: "info",
    submitted: "warning",
    approved: "success",
    rejected: "danger",
    cancelled: "info",
};

function scoreBand(score) {
    if (score >= 80) {
        return "good";
    }
    if (score >= 50) {
        return "watch";
    }
    return "at_risk";
}

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Driver Scorecards (doc 16 §11, Phase E / Slice 1; deepened into the
 * Driver & HR domain's "Driver 360" in the Driver & HR custom-views
 * initiative — see docs/architecture/20-experience-implementation-
 * strategy.md §6b) — a score-filterable, worst-first driver list where
 * tapping a driver now surfaces everything about them in one place:
 * license/qualification identity (editable), recent performance
 * events, outstanding advances, and recent leave requests — mirroring
 * how Fleet Command Center became the Vehicle 360 by deepening its
 * existing expanded card rather than building a second, separate
 * screen with unverified per-record action-params plumbing.
 *
 * **Identity & Qualifications is a real, editable section** (license
 * class/number/expiry, endorsements, qualified vehicle types, and the
 * legacy `deployfleet_risk_score` field), saved via `orm.write` on
 * `hr.employee` — the same inline-edit-plus-save pattern the Fleet
 * Command Center's "Identity & Capacity" section established.
 * **Worth flagging explicitly**: `deployfleet_risk_score`'s own help
 * text (`deployfleet_driver/models/hr_employee.py`) says it would be
 * "lowered by driver-performance incidents once deployfleet_driver_
 * performance is installed" — but that module actually built a wholly
 * separate field (`deployfleet_reliability_score`, the one this screen
 * already surfaced) instead of wiring into this one. `risk_score` is
 * real, stored data (default 100.0, manually adjustable) but not
 * actually touched by any incident logic today — shown here as plain
 * editable data, not treated as a meaningful live metric the way
 * `deployfleet_reliability_score` is.
 *
 * **Advances and Leave sections are real reads with real actions**,
 * not placeholders: Advances shows `deployfleet.driver.advance`
 * records for this driver with Mark Reconciled/Mark Deducted actions
 * wired to the model's actual `action_mark_reconciled()`/
 * `action_mark_deducted()`. Leave shows `deployfleet.leave.request`
 * records with Submit/Approve/Reject/Cancel wired to the model's real
 * state-machine actions, plus a "Request Leave" quick-add form
 * (`orm.create`) — dispatcher-facing, since `deployfleet.leave.
 * request`'s driver-group access is scoped to the driver's own record
 * via a new `ir.rule` (fixed alongside this screen, see doc 20 §6b);
 * this web workspace stays dispatcher/manager-facing like every other
 * screen in `deployfleet_ui`, consistent with drivers' actual
 * self-service channel being the separate React Native driver app, not
 * this module. `action_approve()` on a leave request can raise a real
 * `UserError` if it conflicts with a scheduled trip — surfaced via the
 * same try/catch + notification pattern every write action in this
 * module already uses, not a special case.
 *
 * Soft-coupling: every model here is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetDriverScorecards extends Component {
    static template = "deployfleet_ui.DriverScorecards";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration — see the identical comment in
    // mission_control.js: this is an `ir.actions.client` root component,
    // and Odoo's action manager always injects standard props into it.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.licenseClassOptions = LICENSE_CLASS_OPTIONS;
        this.state = useState({
            loading: true,
            drivers: [],
            eventsByDriverId: {},
            advancesByDriverId: {},
            leaveRequestsByDriverId: {},
            selectedDriverId: null,
            scoreFilter: "all",
            vehicleTypes: [],
            leaveTypes: [],
            editByDriverId: {},
            savingDriverId: null,
            actingId: null,
            newLeaveByDriverId: {},
        });

        onWillStart(() => Promise.all([this.loadDrivers(), this.loadVehicleTypes(), this.loadLeaveTypes()]));
    }

    async loadVehicleTypes() {
        this.state.vehicleTypes = await this.orm.searchRead("deployfleet.vehicle.type", [], ["name"], {
            order: "sequence asc",
        });
    }

    async loadLeaveTypes() {
        this.state.leaveTypes = await this.orm.searchRead("deployfleet.leave.type", [], ["name"], {});
    }

    get scoreFilters() {
        return SCORE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.drivers.length
                    : this.state.drivers.filter((driver) => driver.band === filter.key).length,
        }));
    }

    get filteredDrivers() {
        if (this.state.scoreFilter === "all") {
            return this.state.drivers;
        }
        return this.state.drivers.filter((driver) => driver.band === this.state.scoreFilter);
    }

    scoreBadgeVariant(band) {
        return SCORE_BAND_VARIANT[band] || "info";
    }

    eventTypeLabel(eventType) {
        return EVENT_TYPE_LABEL[eventType] || eventType;
    }

    licenseClassLabel(code) {
        return LICENSE_CLASS_LABEL[code] || code || "—";
    }

    advanceStateLabel(state) {
        return ADVANCE_STATE_LABEL[state] || state;
    }

    advanceStateBadgeVariant(state) {
        return ADVANCE_STATE_BADGE_VARIANT[state] || "info";
    }

    leaveStateLabel(state) {
        return LEAVE_STATE_LABEL[state] || state;
    }

    leaveStateBadgeVariant(state) {
        return LEAVE_STATE_BADGE_VARIANT[state] || "info";
    }

    qualifiedVehicleTypeNames(driver) {
        const ids = driver.deployfleet_qualified_vehicle_type_ids || [];
        return this.state.vehicleTypes
            .filter((t) => ids.includes(t.id))
            .map((t) => t.name)
            .join(", ") || "—";
    }

    async loadDrivers() {
        this.state.loading = true;
        // No `order` here: deployfleet_reliability_score is a computed,
        // unstored Float (hr_employee.py) — asking searchRead to sort by
        // it server-side fails with "Cannot convert ... to SQL because it
        // is not stored". Sort worst-first client-side instead.
        const drivers = await this.orm.searchRead(
            "hr.employee",
            [["deployfleet_is_driver", "=", true]],
            [
                "name",
                "deployfleet_reliability_score",
                "deployfleet_years_experience",
                "deployfleet_accident_count",
                "deployfleet_license_is_expired",
                "deployfleet_license_class",
                "deployfleet_license_number",
                "deployfleet_license_expiry",
                "deployfleet_endorsements",
                "deployfleet_qualified_vehicle_type_ids",
                "deployfleet_risk_score",
            ],
        );
        this.state.drivers = drivers
            .map((driver) => ({ ...driver, band: scoreBand(driver.deployfleet_reliability_score) }))
            .sort((a, b) => a.deployfleet_reliability_score - b.deployfleet_reliability_score);
        this.state.loading = false;
    }

    async onSelectDriver(driverId) {
        if (this.state.selectedDriverId === driverId) {
            this.state.selectedDriverId = null;
            return;
        }
        this.state.selectedDriverId = driverId;

        if (!this.state.editByDriverId[driverId]) {
            const driver = this.state.drivers.find((d) => d.id === driverId);
            this.state.editByDriverId[driverId] = {
                deployfleet_license_class: driver.deployfleet_license_class || "",
                deployfleet_license_number: driver.deployfleet_license_number || "",
                deployfleet_license_expiry: driver.deployfleet_license_expiry || "",
                deployfleet_endorsements: driver.deployfleet_endorsements || "",
                deployfleet_risk_score: driver.deployfleet_risk_score,
            };
        }

        const loads = [];
        if (!this.state.eventsByDriverId[driverId]) {
            loads.push(
                this.orm
                    .searchRead(
                        "deployfleet.driver.performance.event",
                        [["driver_id", "=", driverId]],
                        ["date", "event_type", "description", "score_impact"],
                        { order: "date desc", limit: 10 },
                    )
                    .then((events) => (this.state.eventsByDriverId[driverId] = events)),
            );
        }
        if (!this.state.advancesByDriverId[driverId]) {
            loads.push(
                this.orm
                    .searchRead(
                        "deployfleet.driver.advance",
                        [["driver_id", "=", driverId]],
                        ["purpose", "issued_date", "amount", "outstanding_amount", "state"],
                        { order: "issued_date desc", limit: 10 },
                    )
                    .then((advances) => (this.state.advancesByDriverId[driverId] = advances)),
            );
        }
        if (!this.state.leaveRequestsByDriverId[driverId]) {
            loads.push(
                this.orm
                    .searchRead(
                        "deployfleet.leave.request",
                        [["employee_id", "=", driverId]],
                        ["leave_type_id", "date_from", "date_to", "number_of_days", "state"],
                        { order: "date_from desc", limit: 10 },
                    )
                    .then((requests) => (this.state.leaveRequestsByDriverId[driverId] = requests)),
            );
        }
        await Promise.all(loads);
    }

    async reloadAdvances(driverId) {
        this.state.advancesByDriverId[driverId] = await this.orm.searchRead(
            "deployfleet.driver.advance",
            [["driver_id", "=", driverId]],
            ["purpose", "issued_date", "amount", "outstanding_amount", "state"],
            { order: "issued_date desc", limit: 10 },
        );
    }

    async reloadLeaveRequests(driverId) {
        this.state.leaveRequestsByDriverId[driverId] = await this.orm.searchRead(
            "deployfleet.leave.request",
            [["employee_id", "=", driverId]],
            ["leave_type_id", "date_from", "date_to", "number_of_days", "state"],
            { order: "date_from desc", limit: 10 },
        );
    }

    onEditFieldInput(driverId, field, value) {
        this.state.editByDriverId[driverId][field] = value;
    }

    async onSaveDriverProfile(driverId) {
        const edit = this.state.editByDriverId[driverId];
        this.state.savingDriverId = driverId;
        try {
            await this.orm.write("hr.employee", [driverId], {
                deployfleet_license_class: edit.deployfleet_license_class || false,
                deployfleet_license_number: edit.deployfleet_license_number || false,
                deployfleet_license_expiry: edit.deployfleet_license_expiry || false,
                deployfleet_endorsements: edit.deployfleet_endorsements || false,
                deployfleet_risk_score: parseFloat(edit.deployfleet_risk_score) || 0,
            });
            await this.loadDrivers();
            this.notification.add("Driver profile updated.", { type: "success" });
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingDriverId = null;
        }
    }

    async onAdvanceAction(driverId, advanceId, method) {
        this.state.actingId = advanceId;
        try {
            await this.orm.call("deployfleet.driver.advance", method, [[advanceId]]);
            await this.reloadAdvances(driverId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    async onLeaveAction(driverId, requestId, method) {
        this.state.actingId = requestId;
        try {
            await this.orm.call("deployfleet.leave.request", method, [[requestId]]);
            await this.reloadLeaveRequests(driverId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    onNewLeaveInput(driverId, field, value) {
        this.state.newLeaveByDriverId[driverId] = { ...this.state.newLeaveByDriverId[driverId], [field]: value };
    }

    async onRequestLeave(driverId) {
        const leave = this.state.newLeaveByDriverId[driverId] || {};
        if (!leave.leave_type_id || !leave.date_from || !leave.date_to) {
            this.notification.add("Leave type, start date, and end date are required.", { type: "danger" });
            return;
        }
        this.state.actingId = driverId;
        try {
            await this.orm.create("deployfleet.leave.request", [
                {
                    employee_id: driverId,
                    leave_type_id: parseInt(leave.leave_type_id, 10),
                    date_from: leave.date_from,
                    date_to: leave.date_to,
                    reason: leave.reason || false,
                },
            ]);
            this.state.newLeaveByDriverId[driverId] = {};
            await this.reloadLeaveRequests(driverId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    onOpenDriverForm(driverId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.employee",
            res_id: driverId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.driver_scorecards", DeployfleetDriverScorecards);
