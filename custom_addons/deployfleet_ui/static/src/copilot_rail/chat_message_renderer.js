/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetCard } from "../components/card/card";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";

const VEHICLE_STATUS_BADGE_VARIANT = {
    available: "success", assigned: "info", maintenance: "warning", breakdown: "danger", retired: "info",
};

/**
 * Renders one "vehicle_card" rich-payload component ({type, vehicle_id}) —
 * doc 21 §7/§8 (docs/architecture/21-copilot-rail-architecture.md).
 * Deliberately does its own live ORM read rather than trusting any fields
 * the LLM may have echoed alongside `vehicle_id` in its structured
 * output — the assistant's own knowledge can be stale or wrong, the ORM
 * record can't be.
 */
export class DeployfleetChatVehicleCard extends Component {
    static template = "deployfleet_ui.ChatVehicleCard";
    static components = { DeployfleetCard, DeployfleetStatusBadge };
    static props = { vehicleId: Number };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ vehicle: null, notFound: false });
        onWillStart(() => this.loadVehicle());
    }

    async loadVehicle() {
        // Engineering-audit fix (C-17): an unguarded rejection here (e.g.
        // an AccessError) previously left this card's onWillStart promise
        // permanently unresolved from the render tree's perspective -
        // treated the same as "not found" rather than left to crash the
        // whole chat message.
        try {
            const vehicles = await this.orm.searchRead(
                "deployfleet.vehicle",
                [["id", "=", this.props.vehicleId]],
                ["license_plate", "status", "current_driver_id", "odometer"],
            );
            this.state.vehicle = vehicles[0] || null;
            this.state.notFound = !vehicles[0];
        } catch {
            this.state.vehicle = null;
            this.state.notFound = true;
        }
    }

    get statusBadgeVariant() {
        return VEHICLE_STATUS_BADGE_VARIANT[this.state.vehicle?.status] || "info";
    }
}

/**
 * Renders one "table" rich-payload component ({type, title, columns,
 * rows}) — the assistant's own tool-derived tabular data, rendered as
 * given rather than re-fetched: unlike a vehicle card, a table's rows are
 * typically a tool-call result snapshot (e.g. "due maintenance this
 * week"), not a single record with one authoritative live source to
 * re-check against.
 */
export class DeployfleetChatTable extends Component {
    static template = "deployfleet_ui.ChatTable";
    static props = {
        title: { type: String, optional: true },
        columns: Array,
        rows: Array,
    };
}

/**
 * Dispatches a chat message's `rich_payload.components` array (doc 21
 * §7/§8) to the matching atom by `type` — a thin adapter layer over
 * deployfleet_ui's existing catalog, not a new design language. Two
 * types only for now (vehicle_card, table); an unrecognized type is
 * skipped silently in the template rather than shown as a raw
 * placeholder. Deliberately two explicit `t-if` branches inside one
 * `t-foreach` (preserving the array's original order) rather than a
 * dynamic `t-component` lookup — this module has no prior precedent for
 * dynamic component resolution in a template, and two known types don't
 * need it.
 */
export class DeployfleetChatMessageRenderer extends Component {
    static template = "deployfleet_ui.ChatMessageRenderer";
    static components = { DeployfleetChatVehicleCard, DeployfleetChatTable };
    static props = { components: Array };
}
