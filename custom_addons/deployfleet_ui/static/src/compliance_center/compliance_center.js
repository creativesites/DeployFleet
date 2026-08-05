/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";


import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}
const EXPIRING_SOON_DAYS = 30;

const TABS = [
    { key: "vehicles", label: "Vehicles" },
    { key: "drivers", label: "Drivers" },
];

const STATE_LABEL = { valid: "Valid", expiring_soon: "Expiring Soon", expired: "Expired", missing: "Not on File" };
const STATE_BADGE_VARIANT = { valid: "success", expiring_soon: "warning", expired: "danger", missing: "info" };

/**
 * Compliance Center (Compliance domain) — doc 16 §6's "Compliance
 * Traffic-Light Wall": every vehicle and driver as one row, a
 * red/amber/green chip per document type, answering "who can't legally
 * run today" without opening a single record. The one flagship screen
 * this domain's design conversation confirmed building, closing doc 20's
 * table's one previously-flagged gap.
 *
 * Two walls (Vehicles | Drivers tabs, the same shape as the Calculation
 * Rules & Parameters/AI Predictions two-tab pattern) rather than one
 * mixed table — vehicles and drivers have genuinely different document
 * type columns (4 vs. 2, confirmed by source read of the seeded
 * `deployfleet.compliance.document.type` records).
 *
 * The License column on the Drivers wall reconciles two independent
 * signals — `deployfleet.compliance.document` (the formal, dated
 * record this domain's Driver Documents screen manages) and
 * `hr.employee.deployfleet_license_expiry`/`.deployfleet_license_is_expired`
 * (the quick summary field `deployfleet_driver` already uses for Driver
 * Scorecards/dispatch eligibility) — at DISPLAY TIME ONLY, the same
 * non-invasive union-of-signals pattern already used for the
 * fuel-anomaly reconciliation in Fleet & Vehicles (Vehicle 360): if
 * either signal says expired, the chip shows expired; if no formal
 * document exists at all but the driver's own profile has an expiry
 * date, that date is used to compute a real state (mirroring
 * `deployfleet.compliance.document._state_for_expiry()`'s own 30-day
 * threshold) rather than showing a placeholder "Not on File" for data
 * that actually exists elsewhere. No backend field is written or
 * merged — both sources stay exactly as they are.
 *
 * A vehicle/driver document type with no record at all shows a distinct
 * "Not on File" (info) chip rather than being folded into "Expired" —
 * genuinely different situations (never tracked vs. tracked and lapsed)
 * worth keeping visually distinct.
 *
 * Silent-unless-nonzero attention strip, the same discipline as Mission
 * Control: only surfaces vehicles/drivers that have at least one
 * EXPIRED column, not every row.
 *
 * Soft-coupling: every model referenced here (`deployfleet.vehicle`,
 * `hr.employee`, `deployfleet.compliance.document`/`.document.type`) is
 * a plain runtime string, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetComplianceCenter extends Component {
    static template = "deployfleet_ui.ComplianceCenter";
    static components = { DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            activeTab: "vehicles",
            vehicles: [],
            vehicleDocTypes: [],
            vehicleDocByKey: {},
            drivers: [],
            driverDocTypes: [],
            driverDocByKey: {},
        });

        onWillStart(() => this.loadAll());
    }

    get tabs() {
        return TABS;
    }

    async loadAll() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await Promise.all([this.loadVehicleWall(), this.loadDriverWall()]);
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async loadVehicleWall() {
        const [vehicles, docTypes, documents] = await Promise.all([
            this.orm.searchRead(
                "deployfleet.vehicle", [["status", "!=", "retired"]], ["license_plate", "status"],
                { order: "license_plate asc" },
            ),
            this.orm.searchRead(
                "deployfleet.compliance.document.type", [["applies_to_model", "=", "deployfleet.vehicle"]],
                ["name", "code"], { order: "name asc" },
            ),
            this.orm.searchRead(
                "deployfleet.compliance.document", [["res_model", "=", "deployfleet.vehicle"]],
                ["res_id", "document_type_id", "state"],
            ),
        ]);
        this.state.vehicles = vehicles;
        this.state.vehicleDocTypes = docTypes;
        this.state.vehicleDocByKey = this._latestDocByKey(documents);
    }

    async loadDriverWall() {
        const [drivers, docTypes, documents] = await Promise.all([
            this.orm.searchRead(
                "hr.employee", [["deployfleet_is_driver", "=", true]],
                ["name", "deployfleet_license_expiry", "deployfleet_license_is_expired"],
                { order: "name asc" },
            ),
            this.orm.searchRead(
                "deployfleet.compliance.document.type", [["applies_to_model", "=", "hr.employee"]],
                ["name", "code"], { order: "name asc" },
            ),
            this.orm.searchRead(
                "deployfleet.compliance.document", [["res_model", "=", "hr.employee"]],
                ["res_id", "document_type_id", "state"],
            ),
        ]);
        this.state.drivers = drivers;
        this.state.driverDocTypes = docTypes;
        this.state.driverDocByKey = this._latestDocByKey(documents);
    }

    // Picks the most-recently-created document per (owner, type) pair as
    // the "current" one representing that wall cell — a vehicle/driver
    // can accumulate several documents of the same type over time (e.g.
    // renewed insurance), and there is no "active" flag to distinguish
    // them, so the highest id (most recently logged) wins.
    _latestDocByKey(documents) {
        const byKey = {};
        for (const doc of documents) {
            const key = `${doc.res_id}:${doc.document_type_id[0]}`;
            if (!byKey[key] || doc.id > byKey[key].id) {
                byKey[key] = doc;
            }
        }
        return byKey;
    }

    cellState(byKey, resId, docTypeId) {
        const doc = byKey[`${resId}:${docTypeId}`];
        return doc ? doc.state : "missing";
    }

    _stateFromDate(dateStr) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const expiry = new Date(dateStr);
        expiry.setHours(0, 0, 0, 0);
        const diffDays = Math.round((expiry - today) / (24 * 60 * 60 * 1000));
        if (diffDays < 0) {
            return "expired";
        }
        if (diffDays <= EXPIRING_SOON_DAYS) {
            return "expiring_soon";
        }
        return "valid";
    }

    licenseCellState(driver) {
        let state = this.cellState(this.state.driverDocByKey, driver.id, this._licenseDocTypeId());
        if (state === "missing" && driver.deployfleet_license_expiry) {
            state = this._stateFromDate(driver.deployfleet_license_expiry);
        }
        if (driver.deployfleet_license_is_expired && state !== "expired") {
            state = "expired";
        }
        return state;
    }

    _licenseDocTypeId() {
        const type = this.state.driverDocTypes.find((t) => t.code === "driver_license");
        return type ? type.id : null;
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    get vehiclesWithExpiredCount() {
        return this.state.vehicles.filter((vehicle) =>
            this.state.vehicleDocTypes.some((type) => this.cellState(this.state.vehicleDocByKey, vehicle.id, type.id) === "expired"),
        ).length;
    }

    get driversWithExpiredCount() {
        return this.state.drivers.filter((driver) =>
            this.state.driverDocTypes.some((type) => {
                if (type.code === "driver_license") {
                    return this.licenseCellState(driver) === "expired";
                }
                return this.cellState(this.state.driverDocByKey, driver.id, type.id) === "expired";
            }),
        ).length;
    }

    get hasAttentionItems() {
        return this.vehiclesWithExpiredCount > 0 || this.driversWithExpiredCount > 0;
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

    onOpenDriver(driverId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "hr.employee",
            res_id: driverId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.compliance_center", DeployfleetComplianceCenter);
