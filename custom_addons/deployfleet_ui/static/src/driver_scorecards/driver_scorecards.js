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

function scoreBand(score) {
    if (score >= 80) {
        return "good";
    }
    if (score >= 50) {
        return "watch";
    }
    return "at_risk";
}

/**
 * Driver Scorecards (doc 16 §11, Phase E / Slice 1) — the first Phase E
 * deliverable, chosen deliberately over the other items in doc 16 §11's
 * Phase E list after checking what's actually backed by real data:
 * `deployfleet.vehicle`/`deployfleet.trip` have no GPS/position field
 * anywhere, so Live Fleet Map and Fleet Heat Map would need fabricated
 * coordinates; Load Builder is explicitly gated in doc 16 §7 on the
 * multi-stop shipment model maturing (`deployfleet.trip.shipment.line`
 * today is just "which shipments are on this trip," no stop sequencing);
 * "mobile refinement across all three apps" refers to the driver/
 * dispatcher/customer React Native apps in MOBILE_ARCHITECTURE.md, a
 * different codebase entirely, out of `deployfleet_ui`'s scope. Driver
 * Scorecards is the one item with a complete, real backend already
 * built: `hr.employee.deployfleet_reliability_score` (a genuine computed
 * 0-100 score, `deployfleet_driver_performance`'s own trailing-365-day
 * roll-up of `deployfleet.driver.performance.event` records — accidents,
 * violations, harsh braking, speeding, fuel abuse, late deliveries), plus
 * `deployfleet_years_experience`/`deployfleet_accident_count`/license
 * status already on the driver record from `deployfleet_driver`.
 *
 * A score-filterable driver list (chips: All/Good/Watch/At Risk, live
 * counts) ordered worst-score-first, so the drivers most worth a
 * manager's attention surface at the top rather than requiring a manual
 * sort — the same "so what" discipline as Mission Control's attention
 * strip, applied to a review list rather than a silent-unless-nonzero
 * strip, since a scorecard screen's whole purpose is being scanned, not
 * silently skipped. Tap-to-expand reveals the driver's real recent
 * performance-event history, reusing the same accordion pattern the
 * Dispatch Board and Fleet Command Center already established. Workspace
 * Layer: a manager reviewing driver scorecards is doing sustained review
 * work, not launching/orienting, the same reasoning as those two screens.
 *
 * Soft-coupling: hr.employee/deployfleet.driver.performance.event are
 * referenced as plain runtime strings, the same decision made throughout
 * deployfleet_ui.
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
        this.state = useState({
            loading: true,
            drivers: [],
            eventsByDriverId: {},
            selectedDriverId: null,
            scoreFilter: "all",
        });

        onWillStart(() => this.loadDrivers());
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
        if (!this.state.eventsByDriverId[driverId]) {
            const events = await this.orm.searchRead(
                "deployfleet.driver.performance.event",
                [["driver_id", "=", driverId]],
                ["date", "event_type", "description", "score_impact"],
                { order: "date desc", limit: 10 },
            );
            this.state.eventsByDriverId[driverId] = events;
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
