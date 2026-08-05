/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { localISODate, todayISO, toDate } from "../utils/date_utils";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const TABS = [
    { key: "requests", label: "Requests" },
    { key: "calendar", label: "Calendar" },
    { key: "balances", label: "Balances" },
];

const STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "draft", label: "Draft" },
    { key: "submitted", label: "Submitted" },
    { key: "approved", label: "Approved" },
    { key: "rejected", label: "Rejected" },
];

const STATE_LABEL = {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    rejected: "Rejected",
    cancelled: "Cancelled",
};

const STATE_BADGE_VARIANT = {
    draft: "info",
    submitted: "warning",
    approved: "success",
    rejected: "danger",
    cancelled: "info",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Leave Planner (Driver & HR domain custom-views work) — replaces the
 * stock `deployfleet.leave.request` list/form with a workspace covering
 * requests, a month calendar of who's on leave when, and balances (a
 * model, `deployfleet.leave.balance`, that had no view of any kind
 * anywhere in the backend before this — confirmed by source read).
 *
 * Three tabs, same pattern as the Maintenance Planner: **Requests**
 * (filterable list, the real state-machine actions
 * `action_submit`/`action_approve`/`action_reject`/`action_cancel`,
 * and a "Request Leave" quick-add form); **Calendar** (a hand-rolled
 * CSS-grid month view — no charting library — marking every day within
 * an approved or submitted request's `[date_from, date_to]` range, not
 * just single-day pins, since leave genuinely spans days); **Balances**
 * (a read-only table over `deployfleet.leave.balance` for the current
 * year — real data, no UI existed for this model at all before).
 *
 * `action_approve()` can raise a real `UserError` if the request
 * conflicts with a scheduled trip for that driver — surfaced via the
 * same try/catch + notification pattern every write action in this
 * module already uses.
 *
 * Soft-coupling: every model here is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetLeavePlanner extends Component {
    static template = "deployfleet_ui.LeavePlanner";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.tabs = TABS;
        this.weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        this.state = useState({
            loading: true,
            activeTab: "requests",
            requests: [],
            employees: [],
            leaveTypes: [],
            balances: [],
            stateFilter: "all",
            calendarAnchor: todayISO(),
            actingId: null,
            newRequest: { employee_id: "", leave_type_id: "", date_from: "", date_to: "", reason: "" },
            creating: false,
        });

        onWillStart(() => this.loadAll());
    }

    async loadAll() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const currentYear = new Date().getFullYear();
            const [requests, employees, leaveTypes, balances] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.leave.request",
                    [],
                    ["employee_id", "leave_type_id", "date_from", "date_to", "number_of_days", "state"],
                    { order: "date_from desc" },
                ),
                this.orm.searchRead("hr.employee", [], ["name"], { order: "name asc" }),
                this.orm.searchRead("deployfleet.leave.type", [], ["name"], {}),
                this.orm.searchRead(
                    "deployfleet.leave.balance",
                    [["year", "=", currentYear]],
                    ["employee_id", "leave_type_id", "year", "allocated_days", "used_days", "remaining_days"],
                    { order: "employee_id asc" },
                ),
            ]);
            this.state.requests = requests;
            this.state.employees = employees;
            this.state.leaveTypes = leaveTypes;
            this.state.balances = balances;
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.requests.length
                    : this.state.requests.filter((r) => r.state === filter.key).length,
        }));
    }

    get filteredRequests() {
        if (this.state.stateFilter === "all") {
            return this.state.requests;
        }
        return this.state.requests.filter((r) => r.state === this.state.stateFilter);
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

    async onRequestAction(requestId, method) {
        this.state.actingId = requestId;
        try {
            await this.orm.call("deployfleet.leave.request", method, [[requestId]]);
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    onNewRequestInput(field, value) {
        this.state.newRequest[field] = value;
    }

    async onCreateRequest() {
        const { employee_id, leave_type_id, date_from, date_to, reason } = this.state.newRequest;
        if (!employee_id || !leave_type_id || !date_from || !date_to) {
            this.notification.add("Employee, leave type, and both dates are required.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.leave.request", [
                {
                    employee_id: parseInt(employee_id, 10),
                    leave_type_id: parseInt(leave_type_id, 10),
                    date_from,
                    date_to,
                    reason: reason || false,
                },
            ]);
            this.state.newRequest = { employee_id: "", leave_type_id: "", date_from: "", date_to: "", reason: "" };
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }

    // ---------------------------------------------------------------
    // Calendar
    // ---------------------------------------------------------------

    eventsForDate(iso) {
        return this.state.requests
            .filter((r) => (r.state === "approved" || r.state === "submitted") && iso >= r.date_from && iso <= r.date_to)
            .map((r) => ({
                key: `${r.id}-${iso}`,
                label: `${r.employee_id[1]} — ${r.leave_type_id[1]}`,
                status: r.state === "approved" ? "success" : "warning",
            }));
    }

    buildCalendarDay(date, anchor) {
        const iso = localISODate(date);
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
        this.state.calendarAnchor = localISODate(anchor);
    }

    onCalendarToday() {
        this.state.calendarAnchor = todayISO();
    }
}

registry.category("actions").add("deployfleet_ui.leave_planner", DeployfleetLeavePlanner);
