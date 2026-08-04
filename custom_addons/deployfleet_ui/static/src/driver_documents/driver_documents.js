/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetStatusBadge } from "../components/status_badge/status_badge";
import { DeployfleetStatusPill } from "../components/status_pill/status_pill";

const STATE_FILTERS = [
    { key: "all", label: "All" },
    { key: "valid", label: "Valid" },
    { key: "expiring_soon", label: "Expiring Soon" },
    { key: "expired", label: "Expired" },
];

const STATE_LABEL = { valid: "Valid", expiring_soon: "Expiring Soon", expired: "Expired" };
const STATE_BADGE_VARIANT = { valid: "success", expiring_soon: "warning", expired: "danger" };

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

/**
 * Driver Documents (Compliance domain) — the driver half of
 * `deployfleet.compliance.document`'s polymorphic `res_model`/`res_id`
 * pair, split from Vehicle Documents per the user's explicit choice
 * during this domain's design conversation.
 *
 * Deliberately NOT the same data as Driver Scorecards/Driver 360's own
 * `hr.employee.deployfleet_license_number`/`deployfleet_license_expiry`
 * fields (confirmed by source read: those live directly on `hr.employee`
 * from `deployfleet_driver`, a quick summary used for scoring/dispatch
 * eligibility) — this screen is the formal, dated, attachment-bearing
 * document record. The two are reconciled only at display time on the
 * Compliance Center wall (§ its own module comment), never merged into
 * one backend field — the same non-invasive union-of-signals choice
 * already used for the fuel-anomaly reconciliation in Fleet & Vehicles.
 *
 * Same registry-ledger visual dialect as Vehicle Documents/Parts/Asset
 * Registry. Attachment is lazily loaded per row on expand.
 *
 * Soft-coupling: `deployfleet.compliance.document`/`.document.type`/
 * `hr.employee` are referenced as plain runtime strings, the same
 * decision made throughout `deployfleet_ui`.
 */
export class DeployfleetDriverDocuments extends Component {
    static template = "deployfleet_ui.DriverDocuments";
    static components = { DeployfleetButton, DeployfleetStatusBadge, DeployfleetStatusPill };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            documents: [],
            drivers: [],
            documentTypes: [],
            stateFilter: "all",
            selectedDocumentId: null,
            attachmentByDocumentId: {},
            newDocument: { driver_id: "", document_type_id: "", reference_number: "", issue_date: "", expiry_date: "", attachment: "" },
            creating: false,
            verifyingDocumentId: null,
        });

        onWillStart(() => Promise.all([this.loadDocuments(), this.loadDrivers(), this.loadDocumentTypes()]));
    }

    async loadDocuments() {
        // Deliberately excludes `attachment` — fetched lazily per row on
        // expand, the same discipline as Vehicle Documents/Load Expense
        // Ledger/Delivery Center.
        this.state.loading = true;
        this.state.documents = await this.orm.searchRead(
            "deployfleet.compliance.document",
            [["res_model", "=", "hr.employee"]],
            ["document_type_id", "res_id", "reference_number", "issue_date", "expiry_date", "verified", "state"],
            { order: "expiry_date asc" },
        );
        this.state.loading = false;
    }

    async loadDrivers() {
        this.state.drivers = await this.orm.searchRead(
            "hr.employee", [["deployfleet_is_driver", "=", true]], ["name"], { order: "name asc" },
        );
    }

    async loadDocumentTypes() {
        this.state.documentTypes = await this.orm.searchRead(
            "deployfleet.compliance.document.type",
            [["applies_to_model", "=", "hr.employee"]],
            ["name"],
            { order: "name asc" },
        );
    }

    driverLabel(driverId) {
        const driver = this.state.drivers.find((d) => d.id === driverId);
        return driver ? driver.name : `#${driverId}`;
    }

    get stateFilters() {
        return STATE_FILTERS.map((filter) => ({
            ...filter,
            count:
                filter.key === "all"
                    ? this.state.documents.length
                    : this.state.documents.filter((doc) => doc.state === filter.key).length,
        }));
    }

    get filteredDocuments() {
        if (this.state.stateFilter === "all") {
            return this.state.documents;
        }
        return this.state.documents.filter((doc) => doc.state === this.state.stateFilter);
    }

    stateLabel(state) {
        return STATE_LABEL[state] || state;
    }

    stateBadgeVariant(state) {
        return STATE_BADGE_VARIANT[state] || "info";
    }

    verifyButtonLabel(document) {
        return document.verified ? "Mark Unverified" : "Mark Verified";
    }

    async onSelectDocument(documentId) {
        if (this.state.selectedDocumentId === documentId) {
            this.state.selectedDocumentId = null;
            return;
        }
        this.state.selectedDocumentId = documentId;
        if (!(documentId in this.state.attachmentByDocumentId)) {
            const [record] = await this.orm.read("deployfleet.compliance.document", [documentId], ["attachment"]);
            this.state.attachmentByDocumentId[documentId] = record.attachment || null;
        }
    }

    async onToggleVerified(document) {
        this.state.verifyingDocumentId = document.id;
        try {
            await this.orm.write("deployfleet.compliance.document", [document.id], { verified: !document.verified });
            await this.loadDocuments();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.verifyingDocumentId = null;
        }
    }

    onNewDocumentInput(field, value) {
        this.state.newDocument[field] = value;
    }

    async onAttachmentFileInput(ev) {
        const file = ev.target.files[0];
        if (!file) {
            return;
        }
        this.state.newDocument.attachment = await readFileAsBase64(file);
    }

    async onCreateDocument() {
        const { driver_id, document_type_id, reference_number, issue_date, expiry_date } = this.state.newDocument;
        if (!driver_id) {
            this.notification.add("Choose a driver.", { type: "danger" });
            return;
        }
        if (!document_type_id) {
            this.notification.add("Choose a document type.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            const vals = {
                res_model: "hr.employee",
                res_id: parseInt(driver_id, 10),
                document_type_id: parseInt(document_type_id, 10),
                reference_number: reference_number || false,
                issue_date: issue_date || false,
                expiry_date: expiry_date || false,
            };
            if (this.state.newDocument.attachment) {
                vals.attachment = this.state.newDocument.attachment;
            }
            await this.orm.create("deployfleet.compliance.document", [vals]);
            this.state.newDocument = { driver_id: "", document_type_id: "", reference_number: "", issue_date: "", expiry_date: "", attachment: "" };
            await this.loadDocuments();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }

    onOpenDocumentForm(documentId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "deployfleet.compliance.document",
            res_id: documentId,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("deployfleet_ui.driver_documents", DeployfleetDriverDocuments);
