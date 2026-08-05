/** @odoo-module **/

/**
 * Format a Date's LOCAL calendar date as an ISO "YYYY-MM-DD" string.
 *
 * Deliberately never round-trips through `date.toISOString()`, which
 * converts to UTC first — for any positive-UTC-offset timezone
 * (including Zambia, UTC+2, this product's primary market) that shifts
 * a locally-built midnight Date back one calendar day. Engineering-
 * audit fix (C-16): this exact bug was independently duplicated into
 * trip_board.js, leave_planner.js, and maintenance_planner.js (each
 * had its own todayISO()/buildCalendarDay() using .toISOString()) -
 * fixed once here instead of three times.
 */
export function localISODate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
}

export function todayISO() {
    return localISODate(new Date());
}

/** Parse an ISO "YYYY-MM-DD" string as LOCAL midnight (not UTC). */
export function toDate(iso) {
    return new Date(`${iso}T00:00:00`);
}

export function isoAddDays(iso, days) {
    const d = toDate(iso);
    d.setDate(d.getDate() + days);
    return localISODate(d);
}

export function daysBetweenISO(a, b) {
    return Math.round((toDate(b) - toDate(a)) / 86400000);
}
