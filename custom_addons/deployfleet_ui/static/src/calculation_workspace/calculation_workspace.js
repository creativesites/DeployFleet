/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Calculation Rules & Parameters (Billing & Finance domain) — per the
 * domain-planning decision, gives `deployfleet.calculation.rule`/
 * `.variable`/`.parameter` the Vehicle-Types-style registry treatment
 * rather than leaving them stock admin config: a manager plausibly opens
 * these whenever diesel prices move, not just at initial setup.
 *
 * Two tabs (Rules | Parameters), the same pattern AI Predictions already
 * established for two genuinely different schemas under one workspace.
 * Rules expand to their own nested Variables registry (a rule's formula
 * is meaningless without knowing what its variables resolve to); a
 * Parameter's most common edit — the value itself, when diesel prices
 * move — is a real inline "Update Value" quick-action, not a detour to
 * the stock form.
 *
 * Soft-coupling: `deployfleet.calculation.rule`/`.variable`/`.parameter`
 * are referenced as plain runtime strings, the same decision made
 * throughout `deployfleet_ui`.
 */
export class DeployfleetCalculationWorkspace extends Component {
    static template = "deployfleet_ui.CalculationWorkspace";
    static components = { DeployfleetButton };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            activeTab: "rules",
            rules: [],
            parameters: [],
            vehicleTypes: [],
            selectedRuleId: null,
            variablesByRuleId: {},
            newVariable: { name: "", source: "parameter", parameter_key: "" },
            newRule: { key: "", name: "", formula: "" },
            newParameter: { key: "", name: "", value: "", vehicle_type_id: "" },
            editingParameterId: null,
            editParameterValue: "",
            saving: false,
        });

        onWillStart(() => Promise.all([this.loadRules(), this.loadParameters(), this.loadVehicleTypes()]));
    }

    get tabs() {
        return [
            { key: "rules", label: "Rules" },
            { key: "parameters", label: "Parameters" },
        ];
    }

    onSelectTab(tab) {
        this.state.activeTab = tab;
    }

    async loadRules() {
        this.state.loading = true;
        this.state.rules = await this.orm.searchRead(
            "deployfleet.calculation.rule", [], ["key", "name", "formula"], { order: "name asc" },
        );
        this.state.loading = false;
    }

    async loadParameters() {
        this.state.parameters = await this.orm.searchRead(
            "deployfleet.calculation.parameter",
            [], ["key", "name", "value", "vehicle_type_id"],
            { order: "key asc" },
        );
    }

    async loadVehicleTypes() {
        this.state.vehicleTypes = await this.orm.searchRead(
            "deployfleet.vehicle.type", [], ["name"], { order: "sequence asc" },
        );
    }

    async onSelectRule(ruleId) {
        if (this.state.selectedRuleId === ruleId) {
            this.state.selectedRuleId = null;
            return;
        }
        this.state.selectedRuleId = ruleId;
        this.state.newVariable = { name: "", source: "parameter", parameter_key: "" };
        if (!this.state.variablesByRuleId[ruleId]) {
            await this.loadVariables(ruleId);
        }
    }

    async loadVariables(ruleId) {
        this.state.variablesByRuleId[ruleId] = await this.orm.searchRead(
            "deployfleet.calculation.variable",
            [["rule_id", "=", ruleId]],
            ["name", "source", "parameter_key"],
            { order: "name asc" },
        );
    }

    onNewRuleInput(field, value) {
        this.state.newRule[field] = value;
    }

    async onCreateRule() {
        const { key, name, formula } = this.state.newRule;
        if (!key.trim() || !name.trim() || !formula.trim()) {
            this.notification.add("Key, name, and formula are all required.", { type: "danger" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.create("deployfleet.calculation.rule", [
                { key: key.trim(), name: name.trim(), formula: formula.trim() },
            ]);
            this.state.newRule = { key: "", name: "", formula: "" };
            await this.loadRules();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    onNewVariableInput(field, value) {
        this.state.newVariable[field] = value;
    }

    async onAddVariable(ruleId) {
        if (!this.state.newVariable.name.trim()) {
            this.notification.add("Enter a variable name.", { type: "danger" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.create("deployfleet.calculation.variable", [{
                rule_id: ruleId,
                name: this.state.newVariable.name.trim(),
                source: this.state.newVariable.source,
                parameter_key: this.state.newVariable.parameter_key.trim() || false,
            }]);
            this.state.newVariable = { name: "", source: "parameter", parameter_key: "" };
            await this.loadVariables(ruleId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    onNewParameterInput(field, value) {
        this.state.newParameter[field] = value;
    }

    async onCreateParameter() {
        const { key, name, value, vehicle_type_id } = this.state.newParameter;
        const parsedValue = parseFloat(value);
        if (!key.trim() || !name.trim() || value === "" || Number.isNaN(parsedValue)) {
            this.notification.add("Key, name, and a numeric value are all required.", { type: "danger" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.create("deployfleet.calculation.parameter", [{
                key: key.trim(), name: name.trim(), value: parsedValue,
                vehicle_type_id: vehicle_type_id ? parseInt(vehicle_type_id, 10) : false,
            }]);
            this.state.newParameter = { key: "", name: "", value: "", vehicle_type_id: "" };
            await this.loadParameters();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }

    onStartEditParameter(parameterId, currentValue) {
        this.state.editingParameterId = this.state.editingParameterId === parameterId ? null : parameterId;
        this.state.editParameterValue = currentValue;
    }

    onEditParameterValueInput(value) {
        this.state.editParameterValue = value;
    }

    async onSaveParameterValue(parameterId) {
        const parsedValue = parseFloat(this.state.editParameterValue);
        if (Number.isNaN(parsedValue)) {
            this.notification.add("Enter a numeric value.", { type: "danger" });
            return;
        }
        this.state.saving = true;
        try {
            await this.orm.write("deployfleet.calculation.parameter", [parameterId], { value: parsedValue });
            this.state.editingParameterId = null;
            await this.loadParameters();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.saving = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.calculation_workspace", DeployfleetCalculationWorkspace);
