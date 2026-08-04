/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

const APPLIES_TO_OPTIONS = [
    { value: "deployfleet.vehicle", label: "Vehicle" },
    { value: "hr.employee", label: "Driver" },
];

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function appliesToLabel(model) {
    const match = APPLIES_TO_OPTIONS.find((option) => option.value === model);
    return match ? match.label : model;
}

/**
 * Document Types Workspace (Compliance domain) — the same "even simple
 * master data gets a custom view" treatment doc 20 §2 already applied to
 * the Vehicle Types Workspace, for `deployfleet.compliance.document.type`
 * (name/code/applies_to_model/requires_expiry, no `sequence` field
 * unlike vehicle type — confirmed by source read, so no reorder buttons
 * here). `applies_to_model` is technically a free-text Char on the
 * backend model, but in practice only two values exist anywhere in this
 * codebase (`deployfleet.vehicle`, `hr.employee` — confirmed by grep
 * across every seed data file), so this screen offers a constrained
 * select rather than a free-text input a user could typo.
 *
 * Same registry-ledger visual dialect as Vehicle Types Workspace/Parts
 * Registry. Write access is already correctly manager-only via this
 * model's own ACL (dispatcher read-only, manager full CRUD) — unlike
 * Vehicle Types, no ACL fix was needed here. A denied write surfaces as
 * a friendly notification, the same pattern used everywhere else.
 *
 * Soft-coupling: `deployfleet.compliance.document.type` is referenced as
 * a plain runtime string, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetDocumentTypesWorkspace extends Component {
    static template = "deployfleet_ui.DocumentTypesWorkspace";
    static components = { DeployfleetButton };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            types: [],
            selectedTypeId: null,
            editByTypeId: {},
            newType: { name: "", code: "", applies_to_model: "deployfleet.vehicle", requires_expiry: true },
            savingTypeId: null,
            creating: false,
        });

        onWillStart(() => this.loadTypes());
    }

    get appliesToOptions() {
        return APPLIES_TO_OPTIONS;
    }

    appliesToLabel(model) {
        return appliesToLabel(model);
    }

    async loadTypes() {
        this.state.loading = true;
        this.state.types = await this.orm.searchRead(
            "deployfleet.compliance.document.type",
            [],
            ["name", "code", "applies_to_model", "requires_expiry"],
            { order: "name asc" },
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
        this.state.editByTypeId[typeId] = {
            name: type.name,
            code: type.code || "",
            applies_to_model: type.applies_to_model,
            requires_expiry: type.requires_expiry,
        };
    }

    onEditFieldInput(typeId, field, value) {
        this.state.editByTypeId[typeId][field] = value;
    }

    onEditCheckboxToggle(typeId, field) {
        this.state.editByTypeId[typeId][field] = !this.state.editByTypeId[typeId][field];
    }

    async onSaveType(typeId) {
        const edit = this.state.editByTypeId[typeId];
        if (!edit.name || !edit.name.trim()) {
            this.notification.add("Name is required.", { type: "danger" });
            return;
        }
        this.state.savingTypeId = typeId;
        try {
            await this.orm.write("deployfleet.compliance.document.type", [typeId], {
                name: edit.name.trim(),
                code: edit.code.trim(),
                applies_to_model: edit.applies_to_model,
                requires_expiry: edit.requires_expiry,
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
            await this.orm.unlink("deployfleet.compliance.document.type", [typeId]);
            this.state.selectedTypeId = null;
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingTypeId = null;
        }
    }

    onNewTypeFieldInput(field, value) {
        this.state.newType[field] = value;
    }

    onNewTypeCheckboxToggle() {
        this.state.newType.requires_expiry = !this.state.newType.requires_expiry;
    }

    async onCreateType() {
        if (!this.state.newType.name.trim()) {
            this.notification.add("Enter a name for the new document type.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.compliance.document.type", [{
                name: this.state.newType.name.trim(),
                code: this.state.newType.code.trim(),
                applies_to_model: this.state.newType.applies_to_model,
                requires_expiry: this.state.newType.requires_expiry,
            }]);
            this.state.newType = { name: "", code: "", applies_to_model: "deployfleet.vehicle", requires_expiry: true };
            await this.loadTypes();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.document_types_workspace", DeployfleetDocumentTypesWorkspace);
