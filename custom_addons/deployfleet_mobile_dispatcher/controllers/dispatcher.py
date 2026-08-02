from odoo import http
from odoo.addons.deployfleet_core.controllers.mobile_api import (
    envelope_error,
    envelope_success,
    require_group,
)
from odoo.exceptions import UserError
from odoo.http import request

_DISPATCHER_GROUP = "deployfleet_security.group_deployfleet_dispatcher"


class DeployfleetMobileDispatcherController(http.Controller):
    """REST API backing the dispatcher/fleet-manager mobile app - live
    operations view, trip monitoring, and approvals (see
    docs/architecture/04-module-structure.md's mobile app table). Reuses
    deployfleet_core's shared auth/envelope helpers rather than
    reimplementing them - see that module's controllers/mobile_api.py.
    """

    @http.route("/api/mobile/dispatcher/dashboard", type="http", auth="user", methods=["GET"], csrf=False)
    @require_group(_DISPATCHER_GROUP)
    def dashboard(self, **_kw):
        trip_model = request.env["deployfleet.trip"]
        shipment_model = request.env["deployfleet.shipment"]
        vehicle_model = request.env["deployfleet.vehicle"]
        data = {
            "active_trips": trip_model.search_count([("state", "in", ("planned", "departed"))]),
            "pending_shipments": shipment_model.search_count([("state", "in", ("draft", "confirmed"))]),
            "vehicles_available": vehicle_model.search_count([("status", "=", "available")]),
            "vehicles_assigned": vehicle_model.search_count([("status", "=", "assigned")]),
        }
        return request.make_json_response(envelope_success(data))

    @http.route("/api/mobile/dispatcher/trips", type="http", auth="user", methods=["GET"], csrf=False)
    @require_group(_DISPATCHER_GROUP)
    def trips(self, state=None, **_kw):
        domain = [("state", "in", ("planned", "departed"))] if not state else [("state", "=", state)]
        trips = request.env["deployfleet.trip"].search(domain, order="create_date desc", limit=100)
        data = [self._serialize_trip(trip) for trip in trips]
        return request.make_json_response(envelope_success(data))

    @http.route("/api/mobile/dispatcher/shipments/pending", type="http", auth="user", methods=["GET"], csrf=False)
    @require_group(_DISPATCHER_GROUP)
    def pending_shipments(self, **_kw):
        shipments = request.env["deployfleet.shipment"].search(
            [("state", "in", ("draft", "confirmed"))], order="create_date desc", limit=100
        )
        data = [self._serialize_shipment(shipment) for shipment in shipments]
        return request.make_json_response(envelope_success(data))

    @http.route(
        "/api/mobile/dispatcher/assignments/<int:assignment_id>/confirm",
        type="http", auth="user", methods=["POST"], csrf=False,
    )
    @require_group(_DISPATCHER_GROUP)
    def confirm_assignment(self, assignment_id, override_reason=None, **_kw):
        assignment = request.env["deployfleet.dispatch.assignment"].browse(assignment_id)
        if not assignment.exists():
            return request.make_json_response(envelope_error("Assignment not found."))
        try:
            if override_reason:
                assignment.override_reason = override_reason
            assignment.action_confirm()
        except UserError as exc:
            return request.make_json_response(envelope_error(str(exc)))
        return request.make_json_response(envelope_success({"id": assignment.id, "state": assignment.state}))

    @http.route("/api/mobile/dispatcher/alerts", type="http", auth="user", methods=["GET"], csrf=False)
    @require_group(_DISPATCHER_GROUP)
    def alerts(self, **_kw):
        events = request.env["deployfleet.event.log"].search([], order="create_date desc", limit=20)
        data = [
            {
                "id": event.id,
                "name": event.name,
                "source_model": event.source_model,
                "source_id": event.source_id,
                "create_date": str(event.create_date),
            }
            for event in events
        ]
        return request.make_json_response(envelope_success(data))

    def _serialize_trip(self, trip):
        return {
            "id": trip.id,
            "name": trip.name,
            "state": trip.state,
            "vehicle": trip.vehicle_id.display_name,
            "driver": trip.driver_id.name,
            "planned_departure": str(trip.planned_departure) if trip.planned_departure else None,
            "planned_arrival": str(trip.planned_arrival) if trip.planned_arrival else None,
            "delay_reason": trip.delay_reason,
        }

    def _serialize_shipment(self, shipment):
        return {
            "id": shipment.id,
            "name": shipment.name,
            "state": shipment.state,
            "customer": shipment.customer_id.display_name,
            "pickup": shipment.pickup_depot_id.name,
            "dropoff": shipment.dropoff_depot_id.name,
            "weight_kg": shipment.weight_kg,
        }
