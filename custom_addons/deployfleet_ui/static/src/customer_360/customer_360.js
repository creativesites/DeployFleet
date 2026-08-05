/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";


import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}
const CONTRACT_STATE_BADGE_VARIANT = { draft: "info", active: "success", expired: "warning", terminated: "danger" };
const SHIPMENT_STATE_BADGE_VARIANT = {
    draft: "info", confirmed: "info", assigned: "success", in_transit: "success", delivered: "success", cancelled: "danger",
};

/**
 * Customer 360 (Billing & Finance domain) — per the domain-planning
 * decision, a consolidated account-level view (contracts, active
 * shipments, outstanding balance) closing the customer-workspace
 * question doc 20 §8 had left open when Billing & Finance/Dispatch &
 * Trips were confirmed not to split into a separate Customers domain.
 *
 * "Active shipment" here means not yet delivered or cancelled — the
 * same operational definition Dispatch Board's own state filters
 * already use. "Outstanding balance" is the sum of confirmed invoices
 * whose `payment_state` (deployfleet_accounting) isn't `paid` — a real
 * read over live data, not a stored rollup field, so it's only computed
 * for the customer currently expanded, the same lazy-detail-load
 * discipline every accordion screen in this module already follows
 * rather than an expensive per-row query across every customer at once.
 *
 * Soft-coupling: `deployfleet.contract`/`.shipment`/`.invoice` are
 * referenced as plain runtime strings, the same decision made
 * throughout `deployfleet_ui`.
 */
export class DeployfleetCustomer360 extends Component {
    static template = "deployfleet_ui.Customer360";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetErrorBanner };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            customers: [],
            searchQuery: "",
            selectedCustomerId: null,
            detailByCustomerId: {},
        });

        onWillStart(() => this.loadCustomers());
    }

    get filteredCustomers() {
        const query = this.state.searchQuery.trim().toLowerCase();
        if (!query) {
            return this.state.customers;
        }
        return this.state.customers.filter((customer) => customer.name.toLowerCase().includes(query));
    }

    async loadCustomers() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            this.state.customers = await this.orm.searchRead(
                "res.partner", [["customer_rank", ">", 0]], ["name", "email", "phone"],
                { order: "name asc", limit: 300 },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    onSearchInput(ev) {
        this.state.searchQuery = ev.target.value;
    }

    async onSelectCustomer(customerId) {
        if (this.state.selectedCustomerId === customerId) {
            this.state.selectedCustomerId = null;
            return;
        }
        this.state.selectedCustomerId = customerId;
        if (!this.state.detailByCustomerId[customerId]) {
            await this.loadCustomerDetail(customerId);
        }
    }

    async loadCustomerDetail(customerId) {
        const [contracts, shipments, invoices] = await Promise.all([
            this.orm.searchRead(
                "deployfleet.contract",
                [["customer_id", "=", customerId]],
                ["name", "state", "rate_basis"],
                { order: "create_date desc" },
            ),
            this.orm.searchRead(
                "deployfleet.shipment",
                [["customer_id", "=", customerId], ["state", "not in", ["delivered", "cancelled"]]],
                ["name", "state", "requested_pickup_date"],
                { order: "requested_pickup_date asc" },
            ),
            this.orm.searchRead(
                "deployfleet.invoice",
                [["customer_id", "=", customerId], ["state", "=", "confirmed"]],
                ["name", "amount_total", "payment_state", "invoice_date"],
                { order: "invoice_date desc" },
            ),
        ]);
        const outstandingInvoices = invoices.filter((invoice) => invoice.payment_state !== "paid");
        const outstandingBalance = outstandingInvoices.reduce((total, invoice) => total + invoice.amount_total, 0);
        this.state.detailByCustomerId[customerId] = {
            contracts, shipments, invoices, outstandingInvoices, outstandingBalance,
        };
    }

    contractBadgeVariant(state) {
        return CONTRACT_STATE_BADGE_VARIANT[state] || "info";
    }

    shipmentBadgeVariant(state) {
        return SHIPMENT_STATE_BADGE_VARIANT[state] || "info";
    }

    onOpenCustomerForm(customerId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: customerId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.customer_360", DeployfleetCustomer360);
