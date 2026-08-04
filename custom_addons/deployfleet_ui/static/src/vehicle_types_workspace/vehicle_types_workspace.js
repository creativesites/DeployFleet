/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Vehicle Types Workspace (Fleet & Vehicles domain, doc 20's
 * "every operational entity gets a custom view" rule applied to the
 * smallest model in the domain — `deployfleet.vehicle.type` is nine
 * lines of Python, name/code/sequence, but per doc 20 §2 even a
 * config-shaped screen reads as "ERP" the moment a user opens the
 * stock editable list it replaces.
 *
 * Same registry-ledger visual language as the Parts/Asset Registries
 * (header row, table rows, right-aligned figures) rather than the
 * vehicle-centric accordion pattern — this is a short reference list
 * to scan and occasionally edit, not an operational review queue.
 *
 * Write access is manager-only (`deployfleet.vehicle.type`'s ACL:
 * dispatcher read-only via the base `group_user` grant, full CRUD
 * added for `group_deployfleet_manager` alongside this screen, mirroring
 * the existing Part Category ACL shape). This screen does not hide
 * edit affordances from lower-privileged users — consistent with every
 * other screen in this module, a denied write surfaces as a friendly
 * notification via the same try/catch pattern used everywhere else,
 * not a hidden button.
 *
 * Soft-coupling: `deployfleet.vehicle.type` is referenced as a plain
 * runtime string, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetVehicleTypesWorkspace extends Component {
    static template = "deployfleet_ui.VehicleTypesWorkspace";
    static components = { DeployfleetButton };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js: this is an `ir.actions.client` root
    // component, and Odoo's action manager always injects standard props
    // that an empty props schema here would reject.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            types: [],
            selectedTypeId: null,
            editByTypeId: {},
            newType: { name: "", code: "" },
            savingTypeId: null,
            creating: false,
        });

        onWillStart(() => this.loadTypes());
    }

    async loadTypes() {
        this.state.loading = true;
        this.state.types = await this.orm.searchRead(
            "deployfleet.vehicle.type",
            [],
            ["name", "code", "sequence"],
            { order: "sequence asc" },
        );
        this.state.loading = false;
    }

    onSelectType(typeId) {
        if (this.state.selectedTypeId === typeId) {
            this.state.selectedTypeId = null;
            return;
        }
        this.state.selectedTypeId = typeId;
        const type = this.state.types.find((t) => t.id === typeId);
        this.state.editByTypeId[typeId] = { name: type.name, code: type.code || "" };
    }

    onEditFieldInput(typeId, field, value) {
        this.state.editByTypeId[typeId][field] = value;
    }

    async onSaveType(typeId) {
        const edit = this.state.editByTypeId[typeId];
        if (!edit.name || !edit.name.trim()) {
            this.notification.add("Name is required.", { type: "danger" });
            return;
        }
        this.state.savingTypeId = typeId;
        try {
            await this.orm.write("deployfleet.vehicle.type", [typeId], {
                name: edit.name.trim(),
                code: edit.code.trim(),
            });
            this.state.selectedTypeId = null;
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingTypeId = null;
        }
    }

    async onDeleteType(typeId) {
        this.state.savingTypeId = typeId;
        try {
            await this.orm.unlink("deployfleet.vehicle.type", [typeId]);
            this.state.selectedTypeId = null;
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingTypeId = null;
        }
    }

    async onMoveType(typeId, direction) {
        const index = this.state.types.findIndex((t) => t.id === typeId);
        const swapIndex = index + direction;
        if (swapIndex < 0 || swapIndex >= this.state.types.length) {
            return;
        }
        const current = this.state.types[index];
        const swapWith = this.state.types[swapIndex];
        try {
            await Promise.all([
                this.orm.write("deployfleet.vehicle.type", [current.id], { sequence: swapWith.sequence }),
                this.orm.write("deployfleet.vehicle.type", [swapWith.id], { sequence: current.sequence }),
            ]);
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        }
    }

    onNewTypeFieldInput(field, value) {
        this.state.newType[field] = value;
    }

    async onCreateType() {
        if (!this.state.newType.name.trim()) {
            this.notification.add("Enter a name for the new vehicle type.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        const nextSequence = this.state.types.length
            ? Math.max(...this.state.types.map((t) => t.sequence)) + 10
            : 10;
        try {
            await this.orm.create("deployfleet.vehicle.type", [
                { name: this.state.newType.name.trim(), code: this.state.newType.code.trim(), sequence: nextSequence },
            ]);
            this.state.newType = { name: "", code: "" };
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.vehicle_types_workspace", DeployfleetVehicleTypesWorkspace);
