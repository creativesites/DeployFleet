/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "draft", label: "Draft" },
    { key: "confirmed", label: "Confirmed" },
    { key: "cancelled", label: "Cancelled" },
];

const STATE_BADGE_VARIANT = { draft: "info", confirmed: "success", cancelled: "danger" };

const PAYMENT_STATE_LABEL = {
    not_paid: "Not Paid", in_payment: "In Payment", paid: "Paid",
    partial: "Partial", reversed: "Reversed", invoicing_legacy: "Legacy",
};

const ZRA_STATE_BADGE_VARIANT = { draft: "info", submitted: "info", accepted: "success", rejected: "danger", error: "danger" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Invoice Ledger (Billing & Finance domain, first deliverable) —
 * `deployfleet.invoice` has a real stock list/form (doc 20's table) but
 * nothing joins it to the two things a biller actually needs alongside it:
 * `payment_state` (deployfleet_accounting's related field over
 * `account.move`) and its ZRA Smart Invoice submission status
 * (`deployfleet.zra.submission`, a separate model entirely). Both are
 * genuine cross-module reads this screen performs, not fields the stock
 * form already surfaces together.
 *
 * Confirm/Cancel stay real dispatcher-visible buttons that simply fail
 * with a friendly notification for a read-only role — the same "a view
 * restriction is a UI convenience, not a security boundary" pattern the
 * Insurance Center's claim-action buttons already established, rather
 * than inventing new client-side role-detection. Dispatcher's ACL on
 * `deployfleet.invoice` is read-only by existing design (confirmed during
 * the domain audit) — unchanged here, exactly as decided.
 *
 * Soft-coupling: `deployfleet.invoice`/`.zra.submission` are referenced
 * as plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetInvoiceLedger extends Component {
    static template = "deployfleet_ui.InvoiceLedger";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            invoices: [],
            zraByInvoiceId: {},
            stateFilter: "all",
            selectedInvoiceId: null,
            actingInvoiceId: null,
        });

        onWillStart(() => this.loadInvoices());
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.invoices.length
                    : this.state.invoices.filter((invoice) => invoice.state === filter.key).length,
        }));
    }

    get filteredInvoices() {
        if (this.state.stateFilter === "all") {
            return this.state.invoices;
        }
        return this.state.invoices.filter((invoice) => invoice.state === this.state.stateFilter);
    }

    async loadInvoices() {
        this.state.loading = true;
        const invoices = await this.orm.searchRead(
            "deployfleet.invoice",
            [],
            ["name", "customer_id", "contract_id", "trip_id", "invoice_date", "state", "amount_total", "payment_state"],
            { order: "invoice_date desc" },
        );
        this.state.invoices = invoices;

        const submissions = await this.orm.searchRead(
            "deployfleet.zra.submission",
            [["invoice_id", "in", invoices.map((invoice) => invoice.id)]],
            ["invoice_id", "state", "zra_receipt_no"],
            { order: "create_date desc" },
        );
        const zraByInvoiceId = {};
        for (const submission of submissions) {
            const invoiceId = submission.invoice_id[0];
            if (!zraByInvoiceId[invoiceId]) {
                zraByInvoiceId[invoiceId] = submission;
            }
        }
        this.state.zraByInvoiceId = zraByInvoiceId;
        this.state.loading = false;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    paymentStateLabel(paymentState) {
        return PAYMENT_STATE_LABEL[paymentState] || paymentState || "—";
    }

    zraSubmissionFor(invoiceId) {
        return this.state.zraByInvoiceId[invoiceId] || null;
    }

    zraBadgeVariant(zraState) {
        return ZRA_STATE_BADGE_VARIANT[zraState] || "info";
    }

    onSelectInvoice(invoiceId) {
        this.state.selectedInvoiceId = this.state.selectedInvoiceId === invoiceId ? null : invoiceId;
    }

    async onConfirmInvoice(invoiceId) {
        await this.runAction(invoiceId, "action_confirm");
    }

    async onCancelInvoice(invoiceId) {
        await this.runAction(invoiceId, "action_cancel");
    }

    async runAction(invoiceId, method) {
        this.state.actingInvoiceId = invoiceId;
        try {
            await this.orm.call("deployfleet.invoice", method, [[invoiceId]]);
            await this.loadInvoices();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingInvoiceId = null;
        }
    }

    onOpenInvoiceForm(invoiceId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.invoice",
            res_id: invoiceId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.invoice_ledger", DeployfleetInvoiceLedger);
