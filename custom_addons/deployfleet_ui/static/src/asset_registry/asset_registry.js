/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const STATUS_FILTERS = [
    { key: "all", label: "All" },
    { key: "in_service", label: "In Service" },
    { key: "in_storage", label: "In Storage" },
    { key: "under_repair", label: "Under Repair" },
    { key: "retired", label: "Retired" },
];

const STATUS_LABEL = {
    in_service: "In Service",
    in_storage: "In Storage",
    under_repair: "Under Repair",
    retired: "Retired",
};

const STATUS_BADGE_VARIANT = {
    in_service: "success",
    in_storage: "info",
    under_repair: "warning",
    retired: "info",
};

const ASSET_TYPE_LABEL = {
    trailer: "Trailer",
    container: "Container",
    gps_tracker: "GPS Tracker",
    tool: "Tool",
    safety_equipment: "Safety Equipment",
    other: "Other",
};

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Asset Registry (Fleet & Vehicles custom-views initiative, fourth
 * deliverable) — `deployfleet.asset` (trailers, containers, GPS
 * trackers, tools, safety equipment) has no `vehicle_id` either
 * (confirmed by source read: `location` is deliberately free text, per
 * `deployfleet_asset.py`'s own docstring), so per the same agreed
 * decision as Parts it stays a dedicated screen. Same registry visual
 * language as the Parts Registry (table rows, header row, right-
 * aligned figures) rather than the vehicle-centric card/accordion
 * pattern — visually distinct on purpose, per the agreed decision.
 *
 * Filter chips by status (All/In Service/In Storage/Under
 * Repair/Retired, live counts). Tapping a row expands it to show
 * serial number, location, and acquisition date, plus one-tap status-
 * transition actions wired to the asset's real `action_set_*` methods
 * — the same actionable-not-decorative bar as the Fleet Command
 * Center's vehicle status buttons.
 *
 * Soft-coupling: `deployfleet.asset` is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetAssetRegistry extends Component {
    static template = "deployfleet_ui.AssetRegistry";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component, and Odoo's action manager always injects standard props
    // that an empty props schema here would reject.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            assets: [],
            selectedAssetId: null,
            statusFilter: "all",
            transitioningAssetId: null,
        });

        onWillStart(() => this.loadAssets());
    }

    get statusFilters() {
        return STATUS_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.assets.length
                    : this.state.assets.filter((asset) => asset.status === filter.key).length,
        }));
    }

    get filteredAssets() {
        if (this.state.statusFilter === "all") {
            return this.state.assets;
        }
        return this.state.assets.filter((asset) => asset.status === this.state.statusFilter);
    }

    statusLabel(status) {
        return STATUS_LABEL[status] || status;
    }

    statusBadgeVariant(status) {
        return STATUS_BADGE_VARIANT[status] || "info";
    }

    assetTypeLabel(assetType) {
        return ASSET_TYPE_LABEL[assetType] || assetType;
    }

    async loadAssets() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            this.state.assets = await this.orm.searchRead(
                "deployfleet.asset",
                [],
                ["name", "asset_type", "serial_number", "status", "location", "acquisition_date"],
                { order: "name asc" },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    onSelectAsset(assetId) {
        this.state.selectedAssetId = this.state.selectedAssetId === assetId ? null : assetId;
    }

    async onSetStatus(assetId, actionMethod) {
        this.state.transitioningAssetId = assetId;
        try {
            await this.orm.call("deployfleet.asset", actionMethod, [[assetId]]);
            await this.loadAssets();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.transitioningAssetId = null;
        }
    }

    onOpenAssetForm(assetId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.asset",
            res_id: assetId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.asset_registry", DeployfleetAssetRegistry);
