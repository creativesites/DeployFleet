/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

const EXPIRY_FILTERS = [
    { key: "all", label: "All" },
    { key: "expiring_soon", label: "Expiring Soon" },
    { key: "expired", label: "Expired" },
];

const EXPIRING_SOON_DAYS = 30;

const CLAIM_STATE_LABEL = {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    rejected: "Rejected",
    paid: "Paid",
};

const CLAIM_STATE_BADGE_VARIANT = {
    draft: "info",
    submitted: "warning",
    approved: "success",
    rejected: "danger",
    paid: "success",
};

function daysUntil(dateStr) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const target = new Date(dateStr);
    return Math.round((target - today) / (1000 * 60 * 60 * 24));
}

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * Insurance Center (Fleet & Vehicles domain, doc 20 gap #5) — a
 * fleet-wide insurance view, replacing the two ways policies were
 * previously reachable: a stock list/form, or read-only inside one
 * vehicle's Vehicle 360 detail (doc 16 §7.10). Neither gave a
 * fleet-wide renewal view — which policies expire this month, which
 * vehicles have open claims.
 *
 * Filter chips (All/Expiring Soon/Expired) computed client-side from
 * `end_date` — the policy model itself has no `state` field (confirmed
 * by source read; expiry tracking is delegated to the linked
 * `deployfleet.compliance.document`, which this screen does not read,
 * since the policy's own `end_date` is sufficient for this fleet-wide
 * renewal view). Tap-to-expand reveals the policy's claims plus a real
 * "File a Claim" quick-add form (create-only — dispatcher's ACL on
 * `deployfleet.insurance.claim` is create=1/write=0, a legitimate
 * approval-gate shape unlike the tyre.event ACL gap fixed alongside
 * the Tyre Manager: a dispatcher can file a claim but the
 * submit/approve/reject/paid lifecycle after that is manager-gated by
 * design). Claim state-transition buttons are still shown to every
 * role — consistent with every other screen in this module, a denied
 * write surfaces as a friendly notification, not a hidden button.
 *
 * Soft-coupling: `deployfleet.insurance.policy`/`deployfleet.insurance.
 * claim` are referenced as plain runtime strings, the same decision
 * made throughout `deployfleet_ui`.
 */
export class DeployfleetInsuranceCenter extends Component {
    static template = "deployfleet_ui.InsuranceCenter";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            policies: [],
            expiryFilter: "all",
            selectedPolicyId: null,
            claimsByPolicyId: {},
            newClaimByPolicyId: {},
            actingPolicyId: null,
        });

        onWillStart(() => this.loadPolicies());
    }

    get expiryFilters() {
        return EXPIRY_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.policies.length
                    : this.state.policies.filter((p) => p.expiryBand === filter.key).length,
        }));
    }

    get filteredPolicies() {
        if (this.state.expiryFilter === "all") {
            return this.state.policies;
        }
        return this.state.policies.filter((p) => p.expiryBand === this.state.expiryFilter);
    }

    claimStateLabel(state) {
        return CLAIM_STATE_LABEL[state] || state;
    }

    claimStateBadgeVariant(state) {
        return CLAIM_STATE_BADGE_VARIANT[state] || "info";
    }

    async loadPolicies() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            const policies = await this.orm.searchRead(
                "deployfleet.insurance.policy",
                [],
                ["vehicle_id", "policy_number", "insurer_id", "end_date", "premium_amount"],
                { order: "end_date asc" },
            );
            this.state.policies = policies.map((policy) => {
                const daysLeft = daysUntil(policy.end_date);
                let expiryBand = "ok";
                if (daysLeft < 0) {
                    expiryBand = "expired";
                } else if (daysLeft <= EXPIRING_SOON_DAYS) {
                    expiryBand = "expiring_soon";
                }
                return { ...policy, daysLeft, expiryBand };
            });
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async onSelectPolicy(policyId) {
        if (this.state.selectedPolicyId === policyId) {
            this.state.selectedPolicyId = null;
            return;
        }
        this.state.selectedPolicyId = policyId;
        if (!this.state.claimsByPolicyId[policyId]) {
            const claims = await this.orm.searchRead(
                "deployfleet.insurance.claim",
                [["policy_id", "=", policyId]],
                ["claim_number", "incident_date", "amount_claimed", "amount_approved", "state"],
                { order: "incident_date desc" },
            );
            this.state.claimsByPolicyId[policyId] = claims;
        }
    }

    onNewClaimInput(policyId, field, value) {
        this.state.newClaimByPolicyId[policyId] = { ...this.state.newClaimByPolicyId[policyId], [field]: value };
    }

    async onFileClaim(policyId) {
        const claim = this.state.newClaimByPolicyId[policyId] || {};
        if (!claim.incident_date) {
            this.notification.add("Incident date is required.", { type: "danger" });
            return;
        }
        this.state.actingPolicyId = policyId;
        try {
            await this.orm.create("deployfleet.insurance.claim", [
                {
                    policy_id: policyId,
                    claim_number: claim.claim_number || false,
                    incident_date: claim.incident_date,
                    description: claim.description || false,
                    amount_claimed: claim.amount_claimed ? parseFloat(claim.amount_claimed) : 0,
                },
            ]);
            this.state.newClaimByPolicyId[policyId] = {};
            delete this.state.claimsByPolicyId[policyId];
            await this.onSelectPolicy(policyId);
            this.state.selectedPolicyId = policyId;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingPolicyId = null;
        }
    }

    async onClaimAction(policyId, claimId, method) {
        this.state.actingPolicyId = policyId;
        try {
            await this.orm.call("deployfleet.insurance.claim", method, [[claimId]]);
            delete this.state.claimsByPolicyId[policyId];
            await this.onSelectPolicy(policyId);
            this.state.selectedPolicyId = policyId;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingPolicyId = null;
        }
    }
}

registry.category("actions").add("deployfleet_ui.insurance_center", DeployfleetInsuranceCenter);
