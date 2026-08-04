/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const EXPENSE_TYPE_FILTERS = [
    { key: "all", label: "All" },
    { key: "fuel", label: "Fuel" },
    { key: "toll", label: "Toll" },
    { key: "loading_fee", label: "Loading/Offloading" },
    { key: "permit", label: "Permit" },
    { key: "weighbridge", label: "Weighbridge" },
    { key: "other", label: "Other" },
];

const EXPENSE_TYPE_LABEL = Object.fromEntries(EXPENSE_TYPE_FILTERS.filter((f) => f.key !== "all").map((f) => [f.key, f.label]));

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * Load Expense Ledger (Billing & Finance domain) — replaces
 * `deployfleet.load.expense`'s stock list/form (plain fields, a bare
 * `widget="image"` receipt with no gallery). Fleet-wide, expense-type-
 * filterable registry — same visual dialect as Parts/Asset Registry —
 * plus a "Record Expense" quick-add form with real receipt-photo upload,
 * this module's second Binary-field handler after Delivery Center's
 * signature/photo capture (same FileReader-to-base64 approach, no prior
 * precedent for a third pattern needed).
 *
 * No state machine, no `action_*` methods on this model (confirmed by
 * source read) — this is a flat actuals ledger, the counterpart to the
 * Freight Calculator's cost *estimates*; nothing here duplicates any
 * other screen's functionality.
 *
 * Soft-coupling: `deployfleet.load.expense`/`.shipment` are referenced
 * as plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetLoadExpenseLedger extends Component {
    static template = "deployfleet_ui.LoadExpenseLedger";
    static components = { DeployfleetButton, DeployfleetStatusPill };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            expenses: [],
            shipments: [],
            typeFilter: "all",
            selectedExpenseId: null,
            receiptByExpenseId: {},
            newExpense: { shipment_id: "", expense_type: "fuel", amount: "", receipt: "" },
            creating: false,
        });

        onWillStart(() => Promise.all([this.loadExpenses(), this.loadShipments()]));
    }

    get expenseTypeOptions() {
        return EXPENSE_TYPE_FILTERS.filter((filter) => filter.key !== "all");
    }

    get typeFilters() {
        return EXPENSE_TYPE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.expenses.length
                    : this.state.expenses.filter((expense) => expense.expense_type === filter.key).length,
        }));
    }

    get filteredExpenses() {
        if (this.state.typeFilter === "all") {
            return this.state.expenses;
        }
        return this.state.expenses.filter((expense) => expense.expense_type === this.state.typeFilter);
    }

    expenseTypeLabel(type) {
        return EXPENSE_TYPE_LABEL[type] || type;
    }

    async loadExpenses() {
        // Deliberately excludes `receipt` — a Binary field, fetched lazily
        // per row on expand (onSelectExpense below) rather than pulled as
        // base64 for every row in one list read, the same discipline
        // Delivery Center's signature/photo fields already established.
        this.state.loading = true;
        this.state.expenses = await this.orm.searchRead(
            "deployfleet.load.expense",
            [],
            ["shipment_id", "trip_id", "expense_type", "amount", "recorded_by"],
            { order: "create_date desc", limit: 300 },
        );
        this.state.loading = false;
    }

    async onSelectExpense(expenseId) {
        if (this.state.selectedExpenseId === expenseId) {
            this.state.selectedExpenseId = null;
            return;
        }
        this.state.selectedExpenseId = expenseId;
        if (!(expenseId in this.state.receiptByExpenseId)) {
            const [record] = await this.orm.read("deployfleet.load.expense", [expenseId], ["receipt"]);
            this.state.receiptByExpenseId[expenseId] = record.receipt || null;
        }
    }

    async loadShipments() {
        this.state.shipments = await this.orm.searchRead(
            "deployfleet.shipment", [], ["name"], { order: "requested_pickup_date desc", limit: 200 },
        );
    }

    onNewExpenseInput(field, value) {
        this.state.newExpense[field] = value;
    }

    async onReceiptFileInput(ev) {
        const file = ev.target.files[0];
        if (!file) {
            return;
        }
        this.state.newExpense.receipt = await readFileAsBase64(file);
    }

    async onCreateExpense() {
        const { shipment_id, expense_type, amount } = this.state.newExpense;
        const parsedAmount = parseFloat(amount);
        if (!shipment_id) {
            this.notification.add("Choose a shipment.", { type: "danger" });
            return;
        }
        if (!amount || Number.isNaN(parsedAmount) || parsedAmount <= 0) {
            this.notification.add("Enter an amount greater than zero.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            const vals = {
                shipment_id: parseInt(shipment_id, 10),
                expense_type,
                amount: parsedAmount,
            };
            if (this.state.newExpense.receipt) {
                vals.receipt = this.state.newExpense.receipt;
            }
            await this.orm.create("deployfleet.load.expense", [vals]);
            this.state.newExpense = { shipment_id: "", expense_type: "fuel", amount: "", receipt: "" };
            await this.loadExpenses();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.load_expense_ledger", DeployfleetLoadExpenseLedger);
