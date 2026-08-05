/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Depot Registry (Dispatch & Trips domain, docs/architecture/20-
 * experience-implementation-strategy.md §6c) — replaces the stock
 * `deployfleet.depot` list/form. `deployfleet.depot` is deliberately
 * minimal (name/street/city, per its own class docstring), the same
 * "master data still gets a custom view" case as the Vehicle Types
 * Workspace, and this screen follows that exact precedent: registry-
 * ledger table, tap-to-expand inline edit form, a "New Depot" quick-add.
 *
 * Same real backend ACL fix as the Route Manager: `deployfleet.depot`
 * was previously read-only for `group_deployfleet_dispatcher` despite a
 * dispatcher-visible menu — fixed by granting dispatcher write+create
 * (still no unlink, matching the codebase-wide convention). Delete stays
 * available in this UI (manager-only at the ACL layer) — a denied write
 * surfaces as a friendly notification, the same pattern the Vehicle
 * Types Workspace already established.
 *
 * Soft-coupling: `deployfleet.depot` is referenced as a plain runtime
 * string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetDepotRegistry extends Component {
    static template = "deployfleet_ui.DepotRegistry";
    static components = { DeployfleetButton, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            depots: [],
            selectedDepotId: null,
            editByDepotId: {},
            newDepot: { name: "", street: "", city: "" },
            savingDepotId: null,
            creating: false,
        });

        onWillStart(() => this.loadDepots());
    }

    async loadDepots() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            this.state.depots = await this.orm.searchRead(
                "deployfleet.depot", [], ["name", "street", "city"], { order: "name asc" },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    onSelectDepot(depotId) {
        if (this.state.selectedDepotId === depotId) {
            this.state.selectedDepotId = null;
            return;
        }
        this.state.selectedDepotId = depotId;
        const depot = this.state.depots.find((d) => d.id === depotId);
        this.state.editByDepotId[depotId] = {
            name: depot.name, street: depot.street || "", city: depot.city || "",
        };
    }

    onEditFieldInput(depotId, field, value) {
        this.state.editByDepotId[depotId][field] = value;
    }

    async onSaveDepot(depotId) {
        const edit = this.state.editByDepotId[depotId];
        if (!edit.name || !edit.name.trim()) {
            this.notification.add("Name is required.", { type: "danger" });
            return;
        }
        this.state.savingDepotId = depotId;
        try {
            await this.orm.write("deployfleet.depot", [depotId], {
                name: edit.name.trim(), street: edit.street.trim(), city: edit.city.trim(),
            });
            this.state.selectedDepotId = null;
            await this.loadDepots();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingDepotId = null;
        }
    }

    async onDeleteDepot(depotId) {
        this.state.savingDepotId = depotId;
        try {
            await this.orm.unlink("deployfleet.depot", [depotId]);
            this.state.selectedDepotId = null;
            await this.loadDepots();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingDepotId = null;
        }
    }

    onNewDepotInput(field, value) {
        this.state.newDepot[field] = value;
    }

    async onCreateDepot() {
        if (!this.state.newDepot.name.trim()) {
            this.notification.add("Enter a name for the new depot.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.depot", [
                {
                    name: this.state.newDepot.name.trim(),
                    street: this.state.newDepot.street.trim(),
                    city: this.state.newDepot.city.trim(),
                },
            ]);
            this.state.newDepot = { name: "", street: "", city: "" };
            await this.loadDepots();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.depot_registry", DeployfleetDepotRegistry);
