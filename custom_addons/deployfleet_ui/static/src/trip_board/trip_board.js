/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const TABS = [
    { key: "board", label: "Trips" },
    { key: "calendar", label: "Calendar" },
];

const STATE_FILTERS = [
    { key: "active", label: "Active" },
    { key: "planned", label: "Planned" },
    { key: "departed", label: "Departed" },
    { key: "completed", label: "Completed" },
    { key: "cancelled", label: "Cancelled" },
];

const STATE_LABEL = {
    planned: "Planned",
    departed: "Departed",
    completed: "Completed",
    cancelled: "Cancelled",
};

const STATE_BADGE_VARIANT = {
    planned: "info",
    departed: "warning",
    completed: "success",
    cancelled: "info",
};

const CALENDAR_EVENT_STATUS = {
    planned: "info",
    departed: "warning",
    completed: "success",
    cancelled: "muted",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function todayISO() {
    return new Date().toISOString().slice(0, 10);
}

function toDate(iso) {
    return new Date(`${iso}T00:00:00`);
}

function dateOnly(odooDatetime) {
    // Odoo datetimes come back as "YYYY-MM-DD HH:MM:SS" UTC — the leading
    // 10 characters are the date portion, good enough for calendar-day
    // bucketing without a full timezone conversion (no precedent for one
    // anywhere else in this module).
    return odooDatetime ? odooDatetime.slice(0, 10) : null;
}

/**
 * Trip Board (Dispatch & Trips domain, docs/architecture/20-experience-
 * implementation-strategy.md §6c) — replaces the stock `deployfleet.trip`
 * list/form. Trips are never created through the UI (they're spawned
 * automatically when a dispatch assignment is confirmed — see
 * deployfleet_trip's event-bus subscriber), so this workspace has no
 * create form, only the real state-machine actions
 * (`action_depart`/`action_complete`/`action_report_delay`/
 * `action_cancel`).
 *
 * Two tabs: **Trips** (the same filter-chips-plus-accordion pattern as
 * the Workshop Board — "Active" excludes the terminal completed/
 * cancelled states by default) and **Calendar** (a hand-rolled month
 * grid, reusing the Leave Planner's exact grid-building code, plotting
 * each trip on its `planned_departure` date) — the Calendar tab is what
 * closes doc 20's "Dispatch Calendar" gap (confirmed by source read to
 * not exist anywhere else in the product: zero `<calendar>` views in the
 * whole codebase before this).
 *
 * `action_complete()`'s `odometer_end` kwarg has no stock-form path at
 * all (the stock button is a bare `type="object"` call with zero args) —
 * this workspace is the first place in the product that can actually set
 * it: an inline "Odometer end" input next to the Complete button, passed
 * as a second positional arg only when filled in, so an empty input still
 * calls `action_complete()` with its default (`None`, meaning "leave
 * odometer_end alone") rather than accidentally writing 0/False.
 *
 * "Report Delay" is a small inline reason input + button, available on
 * planned/departed trips — matches `action_report_delay(reason)`'s real
 * signature, which only writes `delay_reason` and does not change state.
 *
 * Workspace Layer, same reasoning as the Dispatch Board/Workshop Board:
 * sustained operational work, not a launch/orientation screen.
 *
 * Soft-coupling: `deployfleet.trip`/`deployfleet.trip.shipment.line` are
 * referenced as plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetTripBoard extends Component {
    static template = "deployfleet_ui.TripBoard";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.tabs = TABS;
        this.weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        this.state = useState({
            loading: true,
            activeTab: "board",
            trips: [],
            shipmentLinesByTripId: {},
            selectedTripId: null,
            stateFilter: "active",
            actingTripId: null,
            odometerEndByTripId: {},
            delayReasonByTripId: {},
            calendarAnchor: todayISO(),
        });

        onWillStart(() => this.loadTrips());
    }

    async loadTrips() {
        this.state.loading = true;
        this.state.trips = await this.orm.searchRead(
            "deployfleet.trip",
            [],
            [
                "name", "vehicle_id", "driver_id", "route_id", "planned_departure", "planned_arrival",
                "actual_departure", "actual_arrival", "odometer_start", "odometer_end", "delay_reason", "state",
            ],
            { order: "planned_departure asc" },
        );
        this.state.loading = false;
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "active"
                    ? this.state.trips.filter((t) => t.state !== "completed" && t.state !== "cancelled").length
                    : this.state.trips.filter((t) => t.state === filter.key).length,
        }));
    }

    get filteredTrips() {
        if (this.state.stateFilter === "active") {
            return this.state.trips.filter((t) => t.state !== "completed" && t.state !== "cancelled");
        }
        return this.state.trips.filter((t) => t.state === this.state.stateFilter);
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
    }

    async onSelectTrip(tripId) {
        if (this.state.selectedTripId === tripId) {
            this.state.selectedTripId = null;
            return;
        }
        this.state.selectedTripId = tripId;
        if (!this.state.shipmentLinesByTripId[tripId]) {
            const lines = await this.orm.searchRead(
                "deployfleet.trip.shipment.line",
                [["trip_id", "=", tripId]],
                ["shipment_id", "weight_portion_kg"],
            );
            this.state.shipmentLinesByTripId[tripId] = lines;
        }
    }

    onOdometerEndInput(tripId, value) {
        this.state.odometerEndByTripId[tripId] = value;
    }

    onDelayReasonInput(tripId, value) {
        this.state.delayReasonByTripId[tripId] = value;
    }

    async onDepart(tripId) {
        this.state.actingTripId = tripId;
        try {
            await this.orm.call("deployfleet.trip", "action_depart", [[tripId]]);
            await this.loadTrips();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTripId = null;
        }
    }

    async onComplete(tripId) {
        this.state.actingTripId = tripId;
        const odometerEnd = this.state.odometerEndByTripId[tripId];
        const args = [[tripId]];
        if (odometerEnd !== undefined && odometerEnd !== null && odometerEnd !== "") {
            args.push(parseFloat(odometerEnd));
        }
        try {
            await this.orm.call("deployfleet.trip", "action_complete", args);
            delete this.state.odometerEndByTripId[tripId];
            await this.loadTrips();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTripId = null;
        }
    }

    async onReportDelay(tripId) {
        const reason = (this.state.delayReasonByTripId[tripId] || "").trim();
        if (!reason) {
            this.notification.add("A delay reason is required.", { type: "danger" });
            return;
        }
        this.state.actingTripId = tripId;
        try {
            await this.orm.call("deployfleet.trip", "action_report_delay", [[tripId], reason]);
            delete this.state.delayReasonByTripId[tripId];
            await this.loadTrips();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTripId = null;
        }
    }

    async onCancel(tripId) {
        this.state.actingTripId = tripId;
        try {
            await this.orm.call("deployfleet.trip", "action_cancel", [[tripId]]);
            await this.loadTrips();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingTripId = null;
        }
    }

    onOpenTripForm(tripId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.trip",
            res_id: tripId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    // ---------------------------------------------------------------
    // Calendar
    // ---------------------------------------------------------------

    eventsForDate(iso) {
        return this.state.trips
            .filter((t) => dateOnly(t.planned_departure) === iso)
            .map((t) => ({
                key: `${t.id}-${iso}`,
                label: `${t.name} — ${t.vehicle_id[1]}`,
                status: CALENDAR_EVENT_STATUS[t.state] || "info",
            }));
    }

    buildCalendarDay(date, anchor) {
        const iso = date.toISOString().slice(0, 10);
        return {
            iso,
            dayNumber: date.getDate(),
            inCurrentMonth: date.getMonth() === anchor.getMonth(),
            isToday: iso === todayISO(),
            events: this.eventsForDate(iso),
        };
    }

    get calendarGridDays() {
        const anchor = toDate(this.state.calendarAnchor);
        const firstOfMonth = new Date(anchor.getFullYear(), anchor.getMonth(), 1);
        const startDate = new Date(firstOfMonth);
        startDate.setDate(firstOfMonth.getDate() - firstOfMonth.getDay());
        const days = [];
        for (let i = 0; i < 42; i++) {
            const d = new Date(startDate);
            d.setDate(startDate.getDate() + i);
            days.push(this.buildCalendarDay(d, anchor));
        }
        return days;
    }

    get calendarLabel() {
        return toDate(this.state.calendarAnchor).toLocaleDateString(undefined, { month: "long", year: "numeric" });
    }

    onCalendarShift(direction) {
        const anchor = toDate(this.state.calendarAnchor);
        anchor.setMonth(anchor.getMonth() + direction);
        this.state.calendarAnchor = anchor.toISOString().slice(0, 10);
    }

    onCalendarToday() {
        this.state.calendarAnchor = todayISO();
    }
}

registry.category("actions").add("deployfleet_ui.trip_board", DeployfleetTripBoard);
