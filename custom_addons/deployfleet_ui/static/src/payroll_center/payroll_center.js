/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const TABS = [
    { key: "payslips", label: "Payslips" },
    { key: "loans", label: "Loans" },
];

const PAYSLIP_STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "draft", label: "Draft" },
    { key: "computed", label: "Computed" },
    { key: "confirmed", label: "Confirmed" },
    { key: "paid", label: "Paid" },
];

const PAYSLIP_STATE_LABEL = { draft: "Draft", computed: "Computed", confirmed: "Confirmed", paid: "Paid" };
const PAYSLIP_STATE_BADGE_VARIANT = { draft: "info", computed: "warning", confirmed: "warning", paid: "success" };

const LOAN_STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "active", label: "Active" },
    { key: "closed", label: "Closed" },
];

const LOAN_STATE_LABEL = { active: "Active", closed: "Closed" };
const LOAN_STATE_BADGE_VARIANT = { active: "success", closed: "info" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function todayISO() {
    return new Date().toISOString().slice(0, 10);
}

/**
 * Payroll Center (Driver & HR domain custom-views work) — combines the
 * Payslips and Loans stock views into one workspace, per the user's
 * explicit choice: they're gated to the same narrow role
 * (`group_deployfleet_hr_payroll_officer`, confirmed from source — a
 * role off the dispatcher -> manager -> owner chain entirely) and
 * already linked in the backend (a payslip's `action_confirm()` calls
 * each active loan's `action_apply_deduction()`).
 *
 * **The most important thing about this screen is what happens when
 * you *don't* have access** — a real, audited gap: `group_deployfleet_
 * manager`/`owner` have zero ACL rows on `deployfleet.payroll.rule`/
 * `payroll.payslip`/`payroll.payslip.line`/`deployfleet.loan` unless
 * separately granted `group_deployfleet_hr_payroll_officer`. That means
 * most managers who reach this screen via the Mega Menu will get an
 * `AccessError` on the very first `searchRead` — `loadAll()` catches
 * that and renders a clean "you don't have access to payroll data"
 * message instead of an unhandled crash, the same defensive discipline
 * the rest of this module reserves for individual write actions,
 * applied here to the initial read itself since read access can't be
 * assumed for this screen the way it safely can everywhere else in
 * `deployfleet_ui`.
 *
 * Two tabs: **Payslips** (filterable list, the real
 * `action_compute()`/`action_confirm()`/`action_mark_paid()` state
 * machine, tap-to-expand showing the computed `line_ids`, a "New
 * Payslip" quick-add form) and **Loans** (filterable list, a "New
 * Loan" quick-add form — no standalone state-transition button exists
 * on this model; `action_apply_deduction()` is only ever called
 * internally by a payslip's own `action_confirm()`, confirmed from
 * source, so this screen doesn't invent a button for it).
 *
 * Soft-coupling: every model here is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetPayrollCenter extends Component {
    static template = "deployfleet_ui.PayrollCenter";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.tabs = TABS;
        this.state = useState({
            loading: true,
            accessError: null,
            activeTab: "payslips",
            payslips: [],
            loans: [],
            employees: [],
            payslipStateFilter: "all",
            loanStateFilter: "all",
            selectedPayslipId: null,
            actingId: null,
            newPayslip: { employee_id: "", period_start: "", period_end: "", base_salary: "" },
            newLoan: { employee_id: "", amount: "", monthly_deduction: "" },
            creatingPayslip: false,
            creatingLoan: false,
        });

        onWillStart(() => this.loadAll());
    }

    async loadAll() {
        this.state.loading = true;
        this.state.accessError = null;
        try {
            const [payslips, loans, employees] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.payroll.payslip",
                    [],
                    ["employee_id", "period_start", "period_end", "base_salary", "gross_pay", "total_deductions", "net_pay", "state"],
                    { order: "period_start desc" },
                ),
                this.orm.searchRead(
                    "deployfleet.loan",
                    [],
                    ["employee_id", "amount", "monthly_deduction", "start_date", "outstanding_balance", "state"],
                    { order: "start_date desc" },
                ),
                this.orm.searchRead("hr.employee", [], ["name"], { order: "name asc" }),
            ]);
            this.state.payslips = payslips;
            this.state.loans = loans;
            this.state.employees = employees;
        } catch (error) {
            this.state.accessError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
    }

    get payslipStateFilters() {
        return PAYSLIP_STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.payslips.length
                    : this.state.payslips.filter((p) => p.state === filter.key).length,
        }));
    }

    get filteredPayslips() {
        if (this.state.payslipStateFilter === "all") {
            return this.state.payslips;
        }
        return this.state.payslips.filter((p) => p.state === this.state.payslipStateFilter);
    }

    get loanStateFilters() {
        return LOAN_STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all" ? this.state.loans.length : this.state.loans.filter((l) => l.state === filter.key).length,
        }));
    }

    get filteredLoans() {
        if (this.state.loanStateFilter === "all") {
            return this.state.loans;
        }
        return this.state.loans.filter((l) => l.state === this.state.loanStateFilter);
    }

    payslipStateLabel(state) {
        return PAYSLIP_STATE_LABEL[state] || state;
    }

    payslipStateBadgeVariant(state) {
        return PAYSLIP_STATE_BADGE_VARIANT[state] || "info";
    }

    loanStateLabel(state) {
        return LOAN_STATE_LABEL[state] || state;
    }

    loanStateBadgeVariant(state) {
        return LOAN_STATE_BADGE_VARIANT[state] || "info";
    }

    async onSelectPayslip(payslipId) {
        if (this.state.selectedPayslipId === payslipId) {
            this.state.selectedPayslipId = null;
            return;
        }
        this.state.selectedPayslipId = payslipId;
        const payslip = this.state.payslips.find((p) => p.id === payslipId);
        if (!payslip.lines) {
            const lines = await this.orm.searchRead(
                "deployfleet.payroll.payslip.line",
                [["payslip_id", "=", payslipId]],
                ["rule_id", "amount"],
            );
            payslip.lines = lines;
        }
    }

    async onPayslipAction(payslipId, method) {
        this.state.actingId = payslipId;
        try {
            await this.orm.call("deployfleet.payroll.payslip", method, [[payslipId]]);
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingId = null;
        }
    }

    onNewPayslipInput(field, value) {
        this.state.newPayslip[field] = value;
    }

    async onCreatePayslip() {
        const { employee_id, period_start, period_end, base_salary } = this.state.newPayslip;
        if (!employee_id || !period_start || !period_end || !base_salary) {
            this.notification.add("Employee, period, and base salary are all required.", { type: "danger" });
            return;
        }
        this.state.creatingPayslip = true;
        try {
            await this.orm.create("deployfleet.payroll.payslip", [
                {
                    employee_id: parseInt(employee_id, 10),
                    period_start,
                    period_end,
                    base_salary: parseFloat(base_salary),
                },
            ]);
            this.state.newPayslip = { employee_id: "", period_start: "", period_end: "", base_salary: "" };
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creatingPayslip = false;
        }
    }

    onNewLoanInput(field, value) {
        this.state.newLoan[field] = value;
    }

    async onCreateLoan() {
        const { employee_id, amount, monthly_deduction } = this.state.newLoan;
        if (!employee_id || !amount || !monthly_deduction) {
            this.notification.add("Employee, amount, and monthly deduction are all required.", { type: "danger" });
            return;
        }
        this.state.creatingLoan = true;
        try {
            await this.orm.create("deployfleet.loan", [
                {
                    employee_id: parseInt(employee_id, 10),
                    amount: parseFloat(amount),
                    monthly_deduction: parseFloat(monthly_deduction),
                    start_date: todayISO(),
                },
            ]);
            this.state.newLoan = { employee_id: "", amount: "", monthly_deduction: "" };
            await this.loadAll();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creatingLoan = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.payroll_center", DeployfleetPayrollCenter);
