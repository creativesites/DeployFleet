/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "draft", label: "Draft" },
    { key: "active", label: "Active" },
    { key: "expired", label: "Expired" },
    { key: "terminated", label: "Terminated" },
];

const STATE_BADGE_VARIANT = { draft: "info", active: "success", expired: "warning", terminated: "danger" };

const RATE_BASIS_LABEL = {
    per_trip: "Per Trip", per_tonnage: "Per Tonnage", per_distance: "Per Distance", per_lane: "Per Lane",
};

const RATE_BASIS_OPTIONS = [
    { key: "per_trip", label: "Per Trip" },
    { key: "per_tonnage", label: "Per Tonnage" },
    { key: "per_distance", label: "Per Distance" },
    { key: "per_lane", label: "Per Lane" },
];

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Contract & Rate Card workspace (Billing & Finance domain) — evolves
 * the stock Contract list/form into the primary screen, and folds Rate
 * Cards in as a nested registry rather than a separate top-level tile:
 * `deployfleet.rate.card` is structurally a contract's own child (cascade
 * FK, unique per contract+vehicle-type) and its stock view was a bare
 * list with no form at all — the same "evolve, don't duplicate" choice
 * as Fleet Command Center absorbing Vehicle Profile's capacity fields.
 *
 * Rate Cards for a contract load lazily on expand, matching the
 * Fleet Command Center/Driver Scorecards accordion pattern used
 * throughout this module.
 *
 * Soft-coupling: `deployfleet.contract`/`.rate.card`/`.vehicle.type` are
 * referenced as plain runtime strings, the same decision made throughout
 * `deployfleet_ui`.
 */
export class DeployfleetContractWorkspace extends Component {
    static template = "deployfleet_ui.ContractWorkspace";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            contracts: [],
            vehicleTypes: [],
            customers: [],
            stateFilter: "all",
            selectedContractId: null,
            rateCardsByContractId: {},
            newRateCard: { vehicle_type_id: "", unit_amount: "" },
            newContract: { customer_id: "", rate_basis: "per_trip", start_date: "" },
            actingContractId: null,
            savingRateCard: false,
            creatingContract: false,
        });

        onWillStart(() => this.loadAllInitialData());
    }

    async loadAllInitialData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await Promise.all([this.loadContracts(), this.loadVehicleTypes(), this.loadCustomers()]);
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    get rateBasisOptions() {
        return RATE_BASIS_OPTIONS;
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.contracts.length
                    : this.state.contracts.filter((contract) => contract.state === filter.key).length,
        }));
    }

    get filteredContracts() {
        if (this.state.stateFilter === "all") {
            return this.state.contracts;
        }
        return this.state.contracts.filter((contract) => contract.state === this.state.stateFilter);
    }

    async loadContracts() {
        this.state.contracts = await this.orm.searchRead(
            "deployfleet.contract",
            [],
            ["name", "customer_id", "rate_basis", "start_date", "end_date", "state"],
            { order: "create_date desc" },
        );
    }

    async loadVehicleTypes() {
        this.state.vehicleTypes = await this.orm.searchRead(
            "deployfleet.vehicle.type", [], ["name"], { order: "sequence asc" },
        );
    }

    async loadCustomers() {
        this.state.customers = await this.orm.searchRead(
            "res.partner", [["customer_rank", ">", 0]], ["name"], { order: "name asc", limit: 200 },
        );
    }

    onNewContractInput(field, value) {
        this.state.newContract[field] = value;
    }

    async onCreateContract() {
        if (!this.state.newContract.customer_id) {
            this.notification.add("Choose a customer for the new contract.", { type: "danger" });
            return;
        }
        this.state.creatingContract = true;
        try {
            await this.orm.create("deployfleet.contract", [{
                customer_id: parseInt(this.state.newContract.customer_id, 10),
                rate_basis: this.state.newContract.rate_basis,
                start_date: this.state.newContract.start_date || undefined,
            }]);
            this.state.newContract = { customer_id: "", rate_basis: "per_trip", start_date: "" };
            await this.loadContracts();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creatingContract = false;
        }
    }

    rateBasisLabel(basis) {
        return RATE_BASIS_LABEL[basis] || basis;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    async onSelectContract(contractId) {
        if (this.state.selectedContractId === contractId) {
            this.state.selectedContractId = null;
            return;
        }
        this.state.selectedContractId = contractId;
        this.state.newRateCard = { vehicle_type_id: "", unit_amount: "" };
        if (!this.state.rateCardsByContractId[contractId]) {
            await this.loadRateCards(contractId);
        }
    }

    async loadRateCards(contractId) {
        this.state.rateCardsByContractId[contractId] = await this.orm.searchRead(
            "deployfleet.rate.card",
            [["contract_id", "=", contractId]],
            ["vehicle_type_id", "unit_amount", "currency_id"],
            { order: "vehicle_type_id asc" },
        );
    }

    onNewRateCardInput(field, value) {
        this.state.newRateCard[field] = value;
    }

    async onAddRateCard(contractId) {
        const unitAmount = parseFloat(this.state.newRateCard.unit_amount);
        if (!this.state.newRateCard.unit_amount || Number.isNaN(unitAmount) || unitAmount <= 0) {
            this.notification.add("Enter a rate greater than zero.", { type: "danger" });
            return;
        }
        this.state.savingRateCard = true;
        try {
            await this.orm.create("deployfleet.rate.card", [{
                contract_id: contractId,
                vehicle_type_id: this.state.newRateCard.vehicle_type_id || false,
                unit_amount: unitAmount,
            }]);
            this.state.newRateCard = { vehicle_type_id: "", unit_amount: "" };
            await this.loadRateCards(contractId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.savingRateCard = false;
        }
    }

    async onActivateContract(contractId) {
        await this.runAction(contractId, "action_activate");
    }

    async onTerminateContract(contractId) {
        await this.runAction(contractId, "action_terminate");
    }

    async runAction(contractId, method) {
        this.state.actingContractId = contractId;
        try {
            await this.orm.call("deployfleet.contract", method, [[contractId]]);
            await this.loadContracts();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingContractId = null;
        }
    }

    onOpenContractForm(contractId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.contract",
            res_id: contractId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.contract_workspace", DeployfleetContractWorkspace);
