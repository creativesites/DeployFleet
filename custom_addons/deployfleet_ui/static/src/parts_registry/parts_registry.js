/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const STOCK_FILTERS = [
    { key: "all", label: "All" },
    { key: "low_stock", label: "Low Stock" },
];

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Parts Registry (Fleet & Vehicles custom-views initiative, third
 * deliverable after the Workshop Board and the Vehicle 360 deepening of
 * the Fleet Command Center) — `deployfleet.part` has no `vehicle_id`
 * anywhere (confirmed by source read before designing, per CLAUDE.md
 * §10's Fleet & Vehicles audit), so per the agreed decision it stays a
 * dedicated screen rather than folding into the vehicle-centric Fleet
 * Command Center, but deliberately styled as a dense inventory ledger
 * (table rows, header row, right-aligned tabular-nums figures) rather
 * than the floating-card/accordion pattern the vehicle-centric screens
 * (Dispatch Board/Fleet Command Center/Workshop Board/Driver
 * Scorecards) all share — a stock registry reads differently from an
 * operational review queue, on purpose, per the same agreed decision.
 *
 * Tapping a row reveals a real "Receive Stock" quick-action (a quantity
 * input wired to the part's actual `action_receive_stock()` method) —
 * the one genuine manual workflow from this screen. Consuming stock is
 * deliberately NOT duplicated here: it already happens as a real side
 * effect of Workshop job cards closing and Tyre replacements, per
 * `deployfleet_workshop`/`deployfleet_tyres`' own source. Silent-
 * unless-actionable: a "Low Stock" badge only appears when
 * `is_low_stock` is true, the same discipline as Mission Control's
 * attention strip.
 *
 * Soft-coupling: `deployfleet.part` is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetPartsRegistry extends Component {
    static template = "deployfleet_ui.PartsRegistry";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component, and Odoo's action manager always injects standard props
    // (`action`, `actionId`, `updateActionState`, `className`, ...) that
    // an empty props schema here would reject.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            parts: [],
            selectedPartId: null,
            stockFilter: "all",
            receiveQuantityByPartId: {},
            receivingPartId: null,
        });

        onWillStart(() => this.loadParts());
    }

    get stockFilters() {
        return STOCK_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.parts.length
                    : this.state.parts.filter((part) => part.is_low_stock).length,
        }));
    }

    get filteredParts() {
        if (this.state.stockFilter === "low_stock") {
            return this.state.parts.filter((part) => part.is_low_stock);
        }
        return this.state.parts;
    }

    async loadParts() {
        this.state.loading = true;
        this.state.parts = await this.orm.searchRead(
            "deployfleet.part",
            [],
            ["name", "reference", "category_id", "quantity_on_hand", "reorder_level", "unit_cost", "is_low_stock"],
            { order: "name asc" },
        );
        this.state.loading = false;
    }

    onSelectPart(partId) {
        this.state.selectedPartId = this.state.selectedPartId === partId ? null : partId;
    }

    onReceiveQuantityInput(partId, value) {
        this.state.receiveQuantityByPartId[partId] = value;
    }

    async onReceiveStock(partId) {
        const rawQuantity = this.state.receiveQuantityByPartId[partId];
        const quantity = parseFloat(rawQuantity);
        if (!rawQuantity || Number.isNaN(quantity) || quantity <= 0) {
            this.notification.add("Enter a quantity greater than zero.", { type: "danger" });
            return;
        }
        this.state.receivingPartId = partId;
        try {
            await this.orm.call("deployfleet.part", "action_receive_stock", [[partId], quantity]);
            this.state.receiveQuantityByPartId[partId] = "";
            await this.loadParts();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.receivingPartId = null;
        }
    }

    onOpenPartForm(partId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.part",
            res_id: partId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.parts_registry", DeployfleetPartsRegistry);
