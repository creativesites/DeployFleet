/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Route Manager (Dispatch & Trips domain, docs/architecture/20-
 * experience-implementation-strategy.md §6c) — replaces the stock
 * `deployfleet.route` list/form. `deployfleet.route` holds no GPS/
 * waypoint data of any kind (confirmed by source read during this
 * domain's audit: `distance_km` is a single manually-entered scalar, and
 * `stop_ids` is just an ordered list of named depot references) — so
 * this is a lane-graph registry, not a map, matching the same GPS-less
 * reality that already ruled out Live Fleet Map/Fleet Heat Map in
 * Phase E.
 *
 * Registry visual dialect (header row, table rows), same as Parts/Asset
 * Registries — a ledger to scan. Tap-to-expand reveals an editable
 * Name/Origin/Destination/Distance form and the route's ordered stop
 * list with an Add Stop control (auto-incrementing sequence, no
 * drag-reorder — the same no-HTML5-drag-drop mobile-first reasoning as
 * the Dispatch Board and Maintenance Planner's Timeline).
 *
 * This screen exists specifically because of a real backend ACL fix
 * made alongside it: `deployfleet.route`/`deployfleet.route.stop` were
 * previously read-only for `group_deployfleet_dispatcher` even though
 * the stock menu was dispatcher-visible — every edit action would have
 * silently failed. Fixed by granting dispatcher write+create (still no
 * unlink, matching the convention every other model in the codebase
 * uses for the dispatcher role) — see deployfleet_route's
 * ir.model.access.csv. "Remove Stop" is still shown to every role
 * (unlink stays manager-only) — a denied write surfaces as a friendly
 * notification here, the same established pattern as the Insurance
 * Center's claim-lifecycle buttons.
 *
 * Soft-coupling: `deployfleet.route`/`deployfleet.route.stop`/
 * `deployfleet.depot` are referenced as plain runtime strings, the same
 * decision made throughout `deployfleet_ui`.
 */
export class DeployfleetRouteManager extends Component {
    static template = "deployfleet_ui.RouteManager";
    static components = { DeployfleetButton };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            routes: [],
            depots: [],
            selectedRouteId: null,
            stopsByRouteId: {},
            editByRouteId: {},
            savingRouteId: null,
            newStopDepotByRouteId: {},
            addingStopRouteId: null,
            removingStopId: null,
            newRoute: { name: "", origin_depot_id: "", destination_depot_id: "", distance_km: "" },
            creating: false,
        });

        onWillStart(() => Promise.all([this.loadRoutes(), this.loadDepots()]));
    }

    async loadRoutes() {
        this.state.loading = true;
        this.state.routes = await this.orm.searchRead(
            "deployfleet.route",
            [],
            ["name", "origin_depot_id", "destination_depot_id", "distance_km"],
            { order: "name asc" },
        );
        this.state.loading = false;
    }

    async loadDepots() {
        this.state.depots = await this.orm.searchRead("deployfleet.depot", [], ["name"], { order: "name asc" });
    }

    async onSelectRoute(route) {
        if (this.state.selectedRouteId === route.id) {
            this.state.selectedRouteId = null;
            return;
        }
        this.state.selectedRouteId = route.id;
        if (!this.state.editByRouteId[route.id]) {
            this.state.editByRouteId[route.id] = {
                name: route.name,
                origin_depot_id: route.origin_depot_id[0],
                destination_depot_id: route.destination_depot_id[0],
                distance_km: route.distance_km,
            };
        }
        if (!this.state.stopsByRouteId[route.id]) {
            await this.loadStops(route.id);
        }
    }

    async loadStops(routeId) {
        this.state.stopsByRouteId[routeId] = await this.orm.searchRead(
            "deployfleet.route.stop",
            [["route_id", "=", routeId]],
            ["sequence", "depot_id"],
            { order: "sequence asc" },
        );
    }

    onEditFieldInput(routeId, field, value) {
        this.state.editByRouteId[routeId] = { ...this.state.editByRouteId[routeId], [field]: value };
    }

    async onSaveRoute(routeId) {
        const edit = this.state.editByRouteId[routeId];
        this.state.savingRouteId = routeId;
        try {
            await this.orm.write("deployfleet.route", [routeId], {
                name: edit.name,
                origin_depot_id: parseInt(edit.origin_depot_id, 10),
                destination_depot_id: parseInt(edit.destination_depot_id, 10),
                distance_km: edit.distance_km ? parseFloat(edit.distance_km) : 0,
            });
            await this.loadRoutes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingRouteId = null;
        }
    }

    onNewStopDepotInput(routeId, value) {
        this.state.newStopDepotByRouteId[routeId] = value;
    }

    async onAddStop(routeId) {
        const depotId = this.state.newStopDepotByRouteId[routeId];
        if (!depotId) {
            this.notification.add("Choose a depot to add as a stop.", { type: "danger" });
            return;
        }
        this.state.addingStopRouteId = routeId;
        try {
            const stops = this.state.stopsByRouteId[routeId] || [];
            const nextSequence = stops.length ? Math.max(...stops.map((s) => s.sequence)) + 10 : 10;
            await this.orm.create("deployfleet.route.stop", [
                { route_id: routeId, depot_id: parseInt(depotId, 10), sequence: nextSequence },
            ]);
            this.state.newStopDepotByRouteId[routeId] = "";
            await this.loadStops(routeId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.addingStopRouteId = null;
        }
    }

    async onRemoveStop(routeId, stopId) {
        this.state.removingStopId = stopId;
        try {
            await this.orm.unlink("deployfleet.route.stop", [stopId]);
            await this.loadStops(routeId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.removingStopId = null;
        }
    }

    onNewRouteInput(field, value) {
        this.state.newRoute[field] = value;
    }

    async onCreateRoute() {
        const { name, origin_depot_id, destination_depot_id, distance_km } = this.state.newRoute;
        if (!name || !origin_depot_id || !destination_depot_id) {
            this.notification.add("Name, origin, and destination are required.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.route", [
                {
                    name,
                    origin_depot_id: parseInt(origin_depot_id, 10),
                    destination_depot_id: parseInt(destination_depot_id, 10),
                    distance_km: distance_km ? parseFloat(distance_km) : 0,
                },
            ]);
            this.state.newRoute = { name: "", origin_depot_id: "", destination_depot_id: "", distance_km: "" };
            await this.loadRoutes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.route_manager", DeployfleetRouteManager);
