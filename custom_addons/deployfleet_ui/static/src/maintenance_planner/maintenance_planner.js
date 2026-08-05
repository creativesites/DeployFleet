/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";
import { DeployfleetAiRecommendationCard } from "../components/ai_recommendation_card/ai_recommendation_card";
import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";
import { localISODate, todayISO, toDate, isoAddDays, daysBetweenISO } from "../utils/date_utils";

const TABS = [
    { key: "overview", label: "Overview" },
    { key: "calendar", label: "Calendar" },
    { key: "timeline", label: "Timeline" },
];

const DUE_SOON_DAYS = 7;
const TIMELINE_DAYS_BEFORE = 7;
const TIMELINE_DAYS_AFTER = 21;
const TRAILING_WINDOW_DAYS = 90;

const VEHICLE_STATUS_LABEL = {
    available: "Available",
    assigned: "Assigned",
    maintenance: "Maintenance",
    breakdown: "Breakdown",
    retired: "Retired",
};

const VEHICLE_STATUS_BADGE_VARIANT = {
    available: "success",
    assigned: "info",
    maintenance: "warning",
    breakdown: "danger",
    retired: "info",
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

const SCORE_BAND_VARIANT = { good: "success", watch: "warning", critical: "danger" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Maintenance Planner (Fleet & Vehicles domain, doc 20 §6a) — the final
 * piece of the Fleet & Vehicles custom-views plan. Answers "what
 * maintenance requires my attention?" in one workspace with three
 * internal views (tabs, not separate menu items, since this is
 * conceptually one screen with different lenses): Overview (attention
 * strip, KPIs, AI recommendations, vehicle health cards), Calendar
 * (day-anchored due-dates and job-card open/close events), and Timeline
 * (a Gantt-style view of job-card downtime and upcoming due-dates per
 * vehicle).
 *
 * **Grounded against what the backend actually has, not the full
 * product-vision brief** — see doc 20 §6a for the complete reasoning.
 * In short: `deployfleet.maintenance.prediction` has no predicted-date
 * field (only risk_score/risk_level/basis), so nothing is plotted on a
 * calendar as if it had a specific date. No inspection model exists
 * anywhere in the backend, so "Inspections" as an event type is not
 * built. `deployfleet.workshop.job.card` has no technician/priority/
 * duration fields, so Timeline bars are day-granularity spans
 * (opened_date -> closed_date or today), not hour-level Gantt bars.
 * "Workshop capacity" has no staffing model behind it, so the real,
 * honest proxy shown is a plain count of open job cards. "Which
 * maintenance can be grouped together" needs a grouping dimension
 * (depot, type) that doesn't exist on the schedule model — not built.
 * "Reschedule" isn't a distinct backend action — `next_due_date` is a
 * stored compute over `last_service_date`/`interval_days`, so the only
 * real lever is `action_record_service` (mark serviced now). "Send
 * Driver Notification" has no backing action either and was dropped
 * rather than faked.
 *
 * Workshop Board stays the execution surface; this screen never
 * duplicates job-card state-advance buttons — it shows job-card state
 * read-only and links out to Workshop Board to work it.
 *
 * **Health Score is a `deployfleet_ui`-computed heuristic, not a
 * backend-stored field** (see `computeHealthScore` below for the exact
 * formula) — built from genuinely real signals (overdue/due-soon
 * schedules, open job cards, AI risk level), but not a value any other
 * screen can rely on, unlike Driver Scorecards' reliability score which
 * comes from a real backend compute.
 *
 * AI recommendations render `deployfleet.maintenance.prediction`'s real
 * fields only and never auto-execute — "Schedule Maintenance" is an
 * explicit human action (creates a job card via the vehicle's existing
 * schedule), the same suggestion -> human-approval -> execute pipeline
 * every other AI surface in this product follows.
 *
 * Soft-coupling: every model here is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetMaintenancePlanner extends Component {
    static template = "deployfleet_ui.MaintenancePlanner";
    static components = {
        DeployfleetButton,
        DeployfleetStatusBadge,
        DeployfleetStatusPill,
        DeployfleetMetricCard,
        DeployfleetAiRecommendationCard,
        DeployfleetErrorBanner,
    };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component, and Odoo's action manager always injects standard props
    // that an empty props schema here would reject.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.tabs = TABS;
        this.weekdayLabels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
        this.state = useState({
            loading: true,
            activeTab: "overview",
            vehicles: [],
            schedules: [],
            jobCards: [],
            predictions: [],
            fuelDistanceThisMonth: 0,
            healthFilter: "all",
            selectedVehicleId: null,
            calendarMode: "month",
            calendarAnchor: todayISO(),
            actingId: null,
            dismissedPredictionVehicleIds: [],
        });

        onWillStart(() => this.loadAll());
    }

    async loadAll() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const monthStart = `${todayISO().slice(0, 7)}-01`;
            const [vehicles, schedules, jobCards, predictions, fuelLogs] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.vehicle",
                    [["status", "!=", "retired"]],
                    ["license_plate", "name", "status", "odometer"],
                    { order: "license_plate asc" },
                ),
                this.orm.searchRead(
                    "deployfleet.maintenance.schedule",
                    [],
                    [
                        "vehicle_id",
                        "name",
                        "last_service_date",
                        "last_service_odometer",
                        "next_due_odometer",
                        "next_due_date",
                        "is_due",
                    ],
                    {},
                ),
                this.orm.searchRead(
                    "deployfleet.workshop.job.card",
                    [],
                    ["name", "vehicle_id", "description", "opened_date", "closed_date", "state", "total_cost", "maintenance_schedule_id"],
                    { order: "opened_date desc", limit: 300 },
                ),
                this.orm.searchRead(
                    "deployfleet.maintenance.prediction",
                    [],
                    ["vehicle_id", "risk_score", "risk_level", "basis", "computed_date"],
                    { order: "computed_date desc" },
                ),
                this.orm.searchRead(
                    "deployfleet.fuel.log",
                    [["date", ">=", monthStart]],
                    ["distance_since_last_km"],
                ),
            ]);

            const latestPredictionByVehicle = {};
            for (const prediction of predictions) {
                const vehicleId = prediction.vehicle_id[0];
                if (!(vehicleId in latestPredictionByVehicle)) {
                    latestPredictionByVehicle[vehicleId] = prediction;
                }
            }

            this.state.vehicles = vehicles;
            this.state.schedules = schedules;
            this.state.jobCards = jobCards;
            this.state.predictions = Object.values(latestPredictionByVehicle);
            this.state.fuelDistanceThisMonth = fuelLogs.reduce((sum, log) => sum + log.distance_since_last_km, 0);
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    // ---------------------------------------------------------------
    // Overview: attention strip, KPIs, AI recommendations, health cards
    // ---------------------------------------------------------------

    isDueSoon(schedule) {
        if (schedule.is_due || !schedule.next_due_date) {
            return false;
        }
        return schedule.next_due_date <= isoAddDays(todayISO(), DUE_SOON_DAYS);
    }

    get overdueSchedules() {
        return this.state.schedules.filter((s) => s.is_due);
    }

    get dueSoonSchedules() {
        return this.state.schedules.filter((s) => this.isDueSoon(s));
    }

    get unavailableVehicles() {
        return this.state.vehicles.filter((v) => v.status === "maintenance" || v.status === "breakdown");
    }

    get atRiskPredictions() {
        return this.state.predictions.filter(
            (p) => p.risk_level !== "low" && !this.state.dismissedPredictionVehicleIds.includes(p.vehicle_id[0]),
        );
    }

    get approvalJobCards() {
        return this.state.jobCards.filter((jc) => jc.state === "approval");
    }

    get attentionItems() {
        return [
            { key: "overdue", label: "Overdue maintenance", status: "danger", count: this.overdueSchedules.length },
            {
                key: "due_soon",
                label: `Due within ${DUE_SOON_DAYS} days`,
                status: "warning",
                count: this.dueSoonSchedules.length,
            },
            { key: "unavailable", label: "Vehicles unavailable", status: "danger", count: this.unavailableVehicles.length },
            { key: "ai_risk", label: "AI predicted risks", status: "ai", count: this.atRiskPredictions.length },
            {
                key: "awaiting_approval",
                label: "Jobs awaiting approval",
                status: "warning",
                count: this.approvalJobCards.length,
            },
        ].filter((item) => item.count > 0);
    }

    get kpiFleetAvailabilityLabel() {
        const total = this.state.vehicles.length;
        if (!total) {
            return "—";
        }
        const available = this.state.vehicles.filter((v) => v.status === "available" || v.status === "assigned").length;
        return `${Math.round((available / total) * 100)}%`;
    }

    get kpiAvgRepairDowntimeLabel() {
        const windowStart = isoAddDays(todayISO(), -TRAILING_WINDOW_DAYS);
        const closed = this.state.jobCards.filter(
            (jc) => jc.state === "closed" && jc.closed_date && jc.opened_date >= windowStart,
        );
        if (!closed.length) {
            return "—";
        }
        const totalDays = closed.reduce((sum, jc) => sum + Math.max(0, daysBetweenISO(jc.opened_date, jc.closed_date)), 0);
        return `${(totalDays / closed.length).toFixed(1)} days`;
    }

    get kpiMaintenanceCostThisMonth() {
        const monthStart = `${todayISO().slice(0, 7)}-01`;
        return this.state.jobCards
            .filter((jc) => jc.opened_date >= monthStart)
            .reduce((sum, jc) => sum + jc.total_cost, 0);
    }

    get kpiPreventiveRatioLabel() {
        const windowStart = isoAddDays(todayISO(), -TRAILING_WINDOW_DAYS);
        const recent = this.state.jobCards.filter((jc) => jc.opened_date >= windowStart);
        if (!recent.length) {
            return "—";
        }
        const preventive = recent.filter((jc) => jc.maintenance_schedule_id).length;
        return `${preventive}:${recent.length - preventive}`;
    }

    get kpiCostPerKm() {
        if (!this.state.fuelDistanceThisMonth) {
            return "—";
        }
        return (this.kpiMaintenanceCostThisMonth / this.state.fuelDistanceThisMonth).toFixed(2);
    }

    computeHealthScore(vehicle) {
        // A deployfleet_ui-computed heuristic, not a backend field — see
        // the class docstring. Weights are deliberate, not tuned against
        // real outcomes yet: overdue schedules hurt most, then open
        // workshop jobs, then a due-soon warning, then AI risk level.
        let score = 100;
        const vehicleSchedules = this.state.schedules.filter((s) => s.vehicle_id[0] === vehicle.id);
        const overdueCount = vehicleSchedules.filter((s) => s.is_due).length;
        const dueSoonCount = vehicleSchedules.filter((s) => this.isDueSoon(s)).length;
        const openJobCardCount = this.state.jobCards.filter(
            (jc) => jc.vehicle_id[0] === vehicle.id && jc.state !== "closed",
        ).length;
        const prediction = this.state.predictions.find((p) => p.vehicle_id[0] === vehicle.id);

        score -= overdueCount * 25;
        score -= dueSoonCount * 10;
        score -= openJobCardCount * 15;
        if (prediction?.risk_level === "high") {
            score -= 30;
        } else if (prediction?.risk_level === "medium") {
            score -= 15;
        }
        return Math.max(0, Math.min(100, score));
    }

    scoreBand(score) {
        if (score >= 70) {
            return "good";
        }
        if (score >= 40) {
            return "watch";
        }
        return "critical";
    }

    scoreBadgeVariant(score) {
        return SCORE_BAND_VARIANT[this.scoreBand(score)];
    }

    statusLabel(status) {
        return VEHICLE_STATUS_LABEL[status] || status;
    }

    statusBadgeVariant(status) {
        return VEHICLE_STATUS_BADGE_VARIANT[status] || "info";
    }

    jobCardStateLabel(state) {
        return JOB_CARD_STATE_LABEL[state] || state;
    }

    jobCardStateBadgeVariant(state) {
        return JOB_CARD_STATE_BADGE_VARIANT[state] || "info";
    }

    predictionTitle(prediction) {
        const levelLabel = prediction.risk_level === "high" ? "High" : "Medium";
        return `${levelLabel} predicted maintenance risk`;
    }

    predictionMeta(prediction) {
        return `Risk score: ${prediction.risk_score}/100`;
    }

    get healthCards() {
        const cards = this.state.vehicles.map((vehicle) => {
            const vehicleSchedules = this.state.schedules.filter((s) => s.vehicle_id[0] === vehicle.id);
            const openJobCards = this.state.jobCards.filter(
                (jc) => jc.vehicle_id[0] === vehicle.id && jc.state !== "closed",
            );
            const prediction = this.state.predictions.find((p) => p.vehicle_id[0] === vehicle.id);
            const overdue = vehicleSchedules.filter((s) => s.is_due);
            const dueSoon = vehicleSchedules.filter((s) => this.isDueSoon(s));
            const nextSchedule = [...vehicleSchedules]
                .filter((s) => s.next_due_date)
                .sort((a, b) => (a.next_due_date < b.next_due_date ? -1 : 1))[0];
            return {
                vehicle,
                score: this.computeHealthScore(vehicle),
                overdueCount: overdue.length,
                dueSoonCount: dueSoon.length,
                openJobCardCount: openJobCards.length,
                nextSchedule,
                prediction: prediction && prediction.risk_level !== "low" ? prediction : null,
                hasApproval: openJobCards.some((jc) => jc.state === "approval"),
            };
        });
        cards.sort((a, b) => a.score - b.score);
        return cards;
    }

    get filteredHealthCards() {
        const filter = this.state.healthFilter;
        if (filter === "overdue") {
            return this.healthCards.filter((c) => c.overdueCount > 0);
        }
        if (filter === "due_soon") {
            return this.healthCards.filter((c) => c.dueSoonCount > 0);
        }
        if (filter === "unavailable") {
            return this.healthCards.filter((c) => c.vehicle.status === "maintenance" || c.vehicle.status === "breakdown");
        }
        if (filter === "ai_risk") {
            return this.healthCards.filter((c) => c.prediction);
        }
        if (filter === "awaiting_approval") {
            return this.healthCards.filter((c) => c.hasApproval);
        }
        return this.healthCards;
    }

    vehicleSchedules(vehicleId) {
        return this.state.schedules.filter((s) => s.vehicle_id[0] === vehicleId);
    }

    vehicleJobCards(vehicleId) {
        return this.state.jobCards.filter((jc) => jc.vehicle_id[0] === vehicleId).slice(0, 5);
    }

    // ---------------------------------------------------------------
    // Calendar
    // ---------------------------------------------------------------

    eventsForDate(iso) {
        const events = [];
        for (const s of this.state.schedules) {
            if (s.next_due_date === iso) {
                events.push({
                    key: `s${s.id}`,
                    label: `${s.vehicle_id[1]} — ${s.name}`,
                    status: s.is_due ? "danger" : this.isDueSoon(s) ? "warning" : "info",
                });
            }
        }
        for (const jc of this.state.jobCards) {
            if (jc.opened_date === iso) {
                events.push({
                    key: `jo${jc.id}`,
                    label: `${jc.vehicle_id[1]} — job opened`,
                    status: this.jobCardStateBadgeVariant(jc.state),
                });
            }
            if (jc.closed_date === iso) {
                events.push({ key: `jc${jc.id}`, label: `${jc.vehicle_id[1]} — completed`, status: "success" });
            }
        }
        return events;
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
        if (this.state.calendarMode === "week") {
            const startOfWeek = new Date(anchor);
            startOfWeek.setDate(anchor.getDate() - anchor.getDay());
            const days = [];
            for (let i = 0; i < 7; i++) {
                const d = new Date(startOfWeek);
                d.setDate(startOfWeek.getDate() + i);
                days.push(this.buildCalendarDay(d, anchor));
            }
            return days;
        }
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
        const anchor = toDate(this.state.calendarAnchor);
        if (this.state.calendarMode === "week") {
            return `Week of ${anchor.toLocaleDateString(undefined, { month: "short", day: "numeric" })}`;
        }
        return anchor.toLocaleDateString(undefined, { month: "long", year: "numeric" });
    }

    onCalendarModeChange(mode) {
        this.state.calendarMode = mode;
    }

    onCalendarShift(direction) {
        const days = this.state.calendarMode === "week" ? 7 : 30;
        this.state.calendarAnchor = isoAddDays(this.state.calendarAnchor, days * direction);
    }

    onCalendarToday() {
        this.state.calendarAnchor = todayISO();
    }

    // ---------------------------------------------------------------
    // Timeline
    // ---------------------------------------------------------------

    get timelineDays() {
        const start = isoAddDays(todayISO(), -TIMELINE_DAYS_BEFORE);
        const totalDays = TIMELINE_DAYS_BEFORE + TIMELINE_DAYS_AFTER + 1;
        const days = [];
        for (let i = 0; i < totalDays; i++) {
            days.push(isoAddDays(start, i));
        }
        return { start, totalDays, days };
    }

    get timelineRows() {
        const { start, totalDays } = this.timelineDays;
        const windowEnd = isoAddDays(start, totalDays - 1);
        const rows = [];
        for (const vehicle of this.state.vehicles) {
            const bars = [];
            for (const jc of this.state.jobCards.filter((j) => j.vehicle_id[0] === vehicle.id)) {
                const barEndRaw = jc.closed_date || todayISO();
                if (barEndRaw < start || jc.opened_date > windowEnd) {
                    continue;
                }
                const barStart = jc.opened_date < start ? start : jc.opened_date;
                const barEnd = barEndRaw > windowEnd ? windowEnd : barEndRaw;
                const left = (daysBetweenISO(start, barStart) / totalDays) * 100;
                const width = Math.max(((daysBetweenISO(barStart, barEnd) + 1) / totalDays) * 100, 100 / totalDays);
                bars.push({
                    id: jc.id,
                    left,
                    width,
                    status: this.jobCardStateBadgeVariant(jc.state),
                    label: jc.description || this.jobCardStateLabel(jc.state),
                });
            }
            const markers = [];
            for (const s of this.state.schedules.filter((sc) => sc.vehicle_id[0] === vehicle.id)) {
                if (!s.next_due_date || s.next_due_date < start || s.next_due_date > windowEnd) {
                    continue;
                }
                markers.push({
                    id: s.id,
                    left: (daysBetweenISO(start, s.next_due_date) / totalDays) * 100,
                    status: s.is_due ? "danger" : "warning",
                    label: s.name,
                });
            }
            if (bars.length || markers.length) {
                rows.push({ vehicle, bars, markers });
            }
        }
        rows.sort((a, b) => b.bars.length - a.bars.length);
        return rows;
    }

    get timelineHiddenVehicleCount() {
        return this.state.vehicles.length - this.timelineRows.length;
    }

    // ---------------------------------------------------------------
    // Actions
    // ---------------------------------------------------------------

    onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
    }

    onAttentionClick(filterKey) {
        this.state.activeTab = "overview";
        this.state.healthFilter = filterKey;
    }

    onSelectVehicle(vehicleId) {
        this.state.selectedVehicleId = this.state.selectedVehicleId === vehicleId ? null : vehicleId;
    }

    async onCreateJobCard(scheduleId) {
        this.state.actingId = scheduleId;
        try {
            await this.orm.call("deployfleet.maintenance.schedule", "action_create_job_card", [[scheduleId]]);
            await this.loadAll();
            this.notification.add("Job card created.", { type: "success" });
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    async onRecordService(scheduleId) {
        this.state.actingId = scheduleId;
        try {
            await this.orm.call("deployfleet.maintenance.schedule", "action_record_service", [[scheduleId]]);
            await this.loadAll();
            this.notification.add("Service recorded.", { type: "success" });
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    async onSetVehicleStatus(vehicleId, method) {
        this.state.actingId = vehicleId;
        try {
            await this.orm.call("deployfleet.vehicle", method, [[vehicleId]]);
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    async onScheduleFromPrediction(vehicleId) {
        const schedule = this.state.schedules.find((s) => s.vehicle_id[0] === vehicleId);
        if (!schedule) {
            this.notification.add(
                "No maintenance schedule found for this vehicle — open its profile to create one.",
                { type: "warning" },
            );
            return;
        }
        await this.onCreateJobCard(schedule.id);
    }

    onDismissPrediction(vehicleId) {
        this.state.dismissedPredictionVehicleIds.push(vehicleId);
    }

    onOpenWorkshopBoard() {
        this.actionService.doAction("deployfleet_ui.action_deployfleet_workshop_board", { clearBreadcrumbs: true });
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

registry.category("actions").add("deployfleet_ui.maintenance_planner", DeployfleetMaintenancePlanner);
