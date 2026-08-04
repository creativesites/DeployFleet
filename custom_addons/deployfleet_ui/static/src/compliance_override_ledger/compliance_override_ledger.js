/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const FLAG_FILTERS = [
    { key: "all", label: "All" },
    { key: "vehicle", label: "Vehicle Expired" },
    { key: "driver", label: "Driver Expired" },
];

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Compliance Overrides Ledger (Compliance domain) — replaces the stock
 * list for `deployfleet.dispatch.compliance.override.log`, per the
 * user's explicit choice during this domain's design conversation
 * (rather than leaving it as the already-locked-down stock list, which
 * showed a raw `assignment_id` reference with no shipment/vehicle/driver
 * context). The stock view is already `create="0" edit="0" delete="0"`
 * — this is a read-only audit trail, the same reasoning behind AI Action
 * History's own read-only ledger — so this workspace adds no write path
 * of its own, only friendly name resolution and filtering.
 *
 * `deployfleet.dispatch.compliance.override.log` has no good default
 * display name of its own (no `name` field, no `_rec_name`) — its
 * `assignment_id` is the only useful reference, and *that* model also
 * has no friendly display name. So this screen does a second batched
 * read on `deployfleet.dispatch.assignment` for the referenced ids,
 * fetching `shipment_id`/`vehicle_id`/`driver_id` (each a Many2one with
 * a real display name), the same batched-lookup pattern already used by
 * Invoice Ledger (ZRA submissions) and Fleet Command Center.
 *
 * Soft-coupling: `deployfleet.dispatch.compliance.override.log`/
 * `.dispatch.assignment` are referenced as plain runtime strings, the
 * same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetComplianceOverrideLedger extends Component {
    static template = "deployfleet_ui.ComplianceOverrideLedger";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            loading: true,
            overrides: [],
            assignmentById: {},
            flagFilter: "all",
        });

        onWillStart(() => this.loadOverrides());
    }

    async loadOverrides() {
        this.state.loading = true;
        this.state.overrides = await this.orm.searchRead(
            "deployfleet.dispatch.compliance.override.log",
            [],
            ["assignment_id", "reason", "overridden_by", "vehicle_had_expired_documents", "driver_had_expired_documents", "create_date"],
            { order: "create_date desc" },
        );
        const assignmentIds = [...new Set(this.state.overrides.map((o) => o.assignment_id[0]))];
        if (assignmentIds.length) {
            const assignments = await this.orm.read(
                "deployfleet.dispatch.assignment", assignmentIds, ["shipment_id", "vehicle_id", "driver_id"],
            );
            this.state.assignmentById = Object.fromEntries(assignments.map((a) => [a.id, a]));
        }
        this.state.loading = false;
    }

    assignmentDetail(assignmentId) {
        return this.state.assignmentById[assignmentId] || null;
    }

    get flagFilters() {
        return FLAG_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.overrides.length
                    : this.state.overrides.filter((o) =>
                        filter.key === "vehicle" ? o.vehicle_had_expired_documents : o.driver_had_expired_documents,
                    ).length,
        }));
    }

    get filteredOverrides() {
        if (this.state.flagFilter === "vehicle") {
            return this.state.overrides.filter((o) => o.vehicle_had_expired_documents);
        }
        if (this.state.flagFilter === "driver") {
            return this.state.overrides.filter((o) => o.driver_had_expired_documents);
        }
        return this.state.overrides;
    }

    onOpenAssignment(assignmentId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.dispatch.assignment",
            res_id: assignmentId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.compliance_override_ledger", DeployfleetComplianceOverrideLedger);
