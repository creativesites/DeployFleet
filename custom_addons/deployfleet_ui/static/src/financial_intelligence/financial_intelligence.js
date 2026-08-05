/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetMetricCard } from "../components/metric_card/metric_card";


import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}
/**
 * Financial Intelligence (Billing & Finance domain) — the deferred
 * flagship from the AI & Intelligence domain audit ("Financial Forecast
 * stays the one deliberately-deferred row, folded into Billing &
 * Finance's own still-open 'Financial Intelligence' gap rather than
 * built twice"). Deepens Mission Control's own naive all-time
 * "Confirmed Revenue" sum into a real answer to "where are we losing
 * money" — five genuine KPIs plus `deployfleet.financial.forecast`'s
 * trend, both read-only rollups over live data, no stored fields added.
 *
 * The one number Rate Card (customer price) vs. Calculation Rule
 * (internal cost estimate) never computes — margin — is deliberately
 * NOT fabricated here from those two models: confirmed by source read,
 * neither carries a per-shipment link the other could join against.
 * Instead, "Gross Margin" is a real, honestly-labeled approximation from
 * data that DOES link cleanly: confirmed invoice revenue minus recorded
 * `deployfleet.load.expense` actuals — excluding fuel logged elsewhere,
 * driver pay, and overhead, stated plainly rather than implied, the same
 * "honestly-labeled approximate cost-per-km" discipline the Maintenance
 * Planner's own KPI row already established.
 *
 * No charting library exists in this module yet (doc 18's own flagged
 * gap) — the forecast trend is a scannable list of recent computations,
 * not a graphic, the same choice every other screen without a charting
 * evaluation has made.
 *
 * Soft-coupling: `deployfleet.invoice`/`.load.expense`/
 * `.financial.forecast` are referenced as plain runtime strings, the
 * same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetFinancialIntelligence extends Component {
    static template = "deployfleet_ui.FinancialIntelligence";
    static components = { DeployfleetMetricCard, DeployfleetErrorBanner };

    setup() {
        this.orm = useService("orm");
        this.state = useState({
            loading: true,
            confirmedRevenue: 0,
            outstandingBalance: 0,
            unpaidInvoiceCount: 0,
            loadExpenseTotal: 0,
            grossMargin: 0,
            forecasts: [],
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const [confirmedInvoices, loadExpenses, forecasts] = await Promise.all([
                this.orm.searchRead(
                    "deployfleet.invoice", [["state", "=", "confirmed"]], ["amount_total", "payment_state"],
                ),
                this.orm.searchRead("deployfleet.load.expense", [], ["amount"]),
                this.orm.searchRead(
                    "deployfleet.financial.forecast", [],
                    ["computed_date", "months_of_history", "forecast_revenue", "forecast_fuel_cost", "basis"],
                    { order: "computed_date desc", limit: 6 },
                ),
            ]);

            const confirmedRevenue = confirmedInvoices.reduce((sum, invoice) => sum + invoice.amount_total, 0);
            const unpaidInvoices = confirmedInvoices.filter((invoice) => invoice.payment_state !== "paid");
            const outstandingBalance = unpaidInvoices.reduce((sum, invoice) => sum + invoice.amount_total, 0);
            const loadExpenseTotal = loadExpenses.reduce((sum, expense) => sum + expense.amount, 0);

            this.state.confirmedRevenue = confirmedRevenue;
            this.state.outstandingBalance = outstandingBalance;
            this.state.unpaidInvoiceCount = unpaidInvoices.length;
            this.state.loadExpenseTotal = loadExpenseTotal;
            this.state.grossMargin = confirmedRevenue - loadExpenseTotal;
            this.state.forecasts = forecasts;
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    formatAmount(amount) {
        return amount.toLocaleString(undefined, { maximumFractionDigits: 0 });
    }

    get formattedConfirmedRevenue() {
        return this.formatAmount(this.state.confirmedRevenue);
    }

    get formattedOutstandingBalance() {
        return this.formatAmount(this.state.outstandingBalance);
    }

    get formattedLoadExpenseTotal() {
        return this.formatAmount(this.state.loadExpenseTotal);
    }

    get formattedGrossMargin() {
        return this.formatAmount(this.state.grossMargin);
    }

    get latestForecast() {
        return this.state.forecasts[0] || null;
    }
}

registry.category("actions").add("deployfleet_ui.financial_intelligence", DeployfleetFinancialIntelligence);
