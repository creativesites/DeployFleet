/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { DeployfleetButton } from "../components/button/button";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

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
 * Delivery Center (Dispatch & Trips domain, docs/architecture/20-
 * experience-implementation-strategy.md §6c) — replaces the stock
 * `deployfleet.delivery` list/form. A ledger of every proof-of-delivery
 * record plus a "Record Delivery" quick-add form.
 *
 * `deployfleet.delivery.create()` is itself the completion event (no
 * `action_*` method exists on this model at all — see the class
 * docstring in deployfleet_delivery/models/deployfleet_delivery.py):
 * creating a record immediately marks the shipment `delivered`. Records
 * are never updated after creation (no write-form precedent, no ACL
 * write grant for dispatcher either), so this workspace has no edit
 * path — only create and browse, matching the backend's own design.
 *
 * The quick-add form's shipment choices are trip-scoped: picking a trip
 * loads that trip's `deployfleet.trip.shipment.line` rows and offers
 * only those shipments, mirroring the domain restriction the stock form
 * already enforces (`_check_shipment_is_on_trip()` would otherwise
 * reject the combination as a `ValidationError`). The trip list itself
 * is scoped to `departed`/`completed` trips — a delivery only makes
 * sense once a trip has actually left.
 *
 * Signature/photo are `Binary` fields with no upload precedent anywhere
 * else in `deployfleet_ui` yet — handled here with a plain `<input
 * type="file">` read via `FileReader` into a base64 string (the format
 * Odoo's ORM expects for a Binary write), not a camera-capture widget;
 * `gps_stamp` stays the free-text "lat,long" placeholder the backend
 * itself documents as a Phase 1 stand-in for real GPS.
 *
 * The ledger's list read deliberately excludes `signature`/`photo` (each
 * a potentially large base64 blob) — they're fetched lazily via a
 * separate `orm.read()` only when a row is expanded, the same
 * lazy-detail discipline every other workspace in this module already
 * follows for its own expensive per-record reads.
 *
 * Workspace Layer, registry visual dialect (header row, table rows) for
 * the ledger — a log to scan, not an operational review queue — with
 * the create form styled like every other quick-add form in this module
 * (Leave Planner, Insurance Center).
 *
 * Soft-coupling: `deployfleet.delivery`/`deployfleet.trip`/
 * `deployfleet.trip.shipment.line` are referenced as plain runtime
 * strings, the same decision made throughout `deployfleet_ui`.
 */
export class DeployfleetDeliveryCenter extends Component {
    static template = "deployfleet_ui.DeliveryCenter";
    static components = { DeployfleetButton, DeployfleetErrorBanner };
    // No `static props` declaration, deliberately — see the identical
    // comment in mission_control.js.

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            deliveries: [],
            trips: [],
            shipmentOptions: [],
            selectedDeliveryId: null,
            detailByDeliveryId: {},
            newDelivery: {
                trip_id: "", shipment_id: "", recipient_name: "", gps_stamp: "",
                signature: "", photo: "",
            },
            creating: false,
        });

        onWillStart(() => this.loadAllInitialData());
    }

    async loadAllInitialData() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            await Promise.all([this.loadDeliveries(), this.loadTrips()]);
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    async loadDeliveries() {
        this.state.deliveries = await this.orm.searchRead(
            "deployfleet.delivery",
            [],
            ["name", "trip_id", "shipment_id", "delivered_at", "recipient_name"],
            { order: "delivered_at desc" },
        );
    }

    async loadTrips() {
        this.state.trips = await this.orm.searchRead(
            "deployfleet.trip",
            [["state", "in", ["departed", "completed"]]],
            ["name", "vehicle_id"],
            { order: "planned_departure desc" },
        );
    }

    async onSelectDelivery(deliveryId) {
        if (this.state.selectedDeliveryId === deliveryId) {
            this.state.selectedDeliveryId = null;
            return;
        }
        this.state.selectedDeliveryId = deliveryId;
        if (!this.state.detailByDeliveryId[deliveryId]) {
            const [detail] = await this.orm.read(
                "deployfleet.delivery", [deliveryId], ["gps_stamp", "signature", "photo"],
            );
            this.state.detailByDeliveryId[deliveryId] = detail;
        }
    }

    async onNewDeliveryTripInput(value) {
        this.state.newDelivery.trip_id = value;
        this.state.newDelivery.shipment_id = "";
        this.state.shipmentOptions = [];
        if (!value) {
            return;
        }
        const lines = await this.orm.searchRead(
            "deployfleet.trip.shipment.line",
            [["trip_id", "=", parseInt(value, 10)]],
            ["shipment_id"],
        );
        this.state.shipmentOptions = lines.map((line) => ({ id: line.shipment_id[0], name: line.shipment_id[1] }));
    }

    onNewDeliveryInput(field, value) {
        this.state.newDelivery[field] = value;
    }

    async onFileInput(field, ev) {
        const file = ev.target.files[0];
        if (!file) {
            return;
        }
        this.state.newDelivery[field] = await readFileAsBase64(file);
    }

    async onCreateDelivery() {
        const { trip_id, shipment_id, recipient_name, gps_stamp, signature, photo } = this.state.newDelivery;
        if (!trip_id || !shipment_id) {
            this.notification.add("Trip and shipment are required.", { type: "danger" });
            return;
        }
        this.state.creating = true;
        try {
            await this.orm.create("deployfleet.delivery", [
                {
                    trip_id: parseInt(trip_id, 10),
                    shipment_id: parseInt(shipment_id, 10),
                    recipient_name: recipient_name || false,
                    gps_stamp: gps_stamp || false,
                    signature: signature || false,
                    photo: photo || false,
                },
            ]);
            this.state.newDelivery = {
                trip_id: "", shipment_id: "", recipient_name: "", gps_stamp: "", signature: "", photo: "",
            };
            this.state.shipmentOptions = [];
            await this.loadDeliveries();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creating = false;
        }
    }
}

registry.category("actions").add("deployfleet_ui.delivery_center", DeployfleetDeliveryCenter);
