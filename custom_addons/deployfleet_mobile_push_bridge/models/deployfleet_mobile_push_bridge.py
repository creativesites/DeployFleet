import logging

from odoo import api, models

try:
    import requests
except ImportError:  # pragma: no cover — declared in __manifest__.py external_dependencies
    requests = None

_logger = logging.getLogger(__name__)

_EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

# Which events push a notification, who to, and what to say. A module
# adding a new push-worthy event edits this table - see
# deployfleet_notifications for the equivalent, generic, data-driven
# version of this same idea; this one is intentionally a small fixed
# table instead, since unlike deployfleet_notifications this module has
# no persistent "rule" model of its own to keep the Expo dependency
# scoped to exactly this bridge.
_EVENT_HANDLERS = {
    "deployfleet.trip.delayed": ("shipment_customer", "Trip Delayed", "Your shipment has been delayed: {reason}"),
    "deployfleet.delivery.completed": ("shipment_customer", "Delivered", "Your shipment has been delivered."),
    "deployfleet.dispatch.assigned": ("assigned_driver", "New Assignment", "You've been assigned to a new shipment."),
    "deployfleet.vehicle.breakdown": ("dispatchers", "Vehicle Breakdown", "{vehicle} has been reported broken down."),
}

_SHIPMENT_LOOKUP = {
    "deployfleet.shipment": lambda record: record,
    "deployfleet.dispatch.assignment": lambda record: record.shipment_id,
    "deployfleet.delivery": lambda record: record.shipment_id,
    "deployfleet.trip": lambda record: record.shipment_line_ids.shipment_id,
}
_DRIVER_LOOKUP = {
    "deployfleet.dispatch.assignment": lambda record: record.driver_id,
    "deployfleet.trip": lambda record: record.driver_id,
}


class DeployfleetMobilePushBridge(models.AbstractModel):
    """Event-bus subscriber that turns a fixed set of operational events
    into Expo push notifications to the right registered device(s) - see
    docs/architecture/02-reuse-strategy.md §6's "FCM/Expo push not wired"
    known gap this module closes."""

    _name = "deployfleet.mobile.push.bridge"
    _description = "DeployFleet Mobile Push Bridge"

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        handler = _EVENT_HANDLERS.get(event_name)
        if not handler:
            return
        recipient_type, title, template = handler
        partners = self._resolve_recipients(recipient_type, source_model, source_id)
        if not partners:
            return
        try:
            body = template.format(**(payload or {}))
        except (KeyError, IndexError):
            body = title

        devices = self.env["deployfleet.mobile.device"].sudo().search([
            ("user_id.partner_id", "in", partners.ids), ("active", "=", True),
        ])
        for device in devices:
            self._send_push(device, title, body)

    def _resolve_recipients(self, recipient_type, source_model, source_id):
        if recipient_type == "dispatchers":
            group = self.env.ref("deployfleet_security.group_deployfleet_dispatcher")
            return group.users.partner_id
        if recipient_type == "shipment_customer":
            return self._get_shipments(source_model, source_id).customer_id
        if recipient_type == "assigned_driver":
            driver = self._get_driver(source_model, source_id)
            return driver.user_id.partner_id if driver and driver.user_id else self.env["res.partner"]
        return self.env["res.partner"]

    def _get_shipments(self, source_model, source_id):
        lookup = _SHIPMENT_LOOKUP.get(source_model)
        if not lookup or source_model not in self.env:
            return self.env["deployfleet.shipment"]
        record = self.env[source_model].browse(source_id)
        if not record.exists():
            return self.env["deployfleet.shipment"]
        return lookup(record)

    def _get_driver(self, source_model, source_id):
        lookup = _DRIVER_LOOKUP.get(source_model)
        if not lookup or source_model not in self.env:
            return self.env["hr.employee"]
        record = self.env[source_model].browse(source_id)
        if not record.exists():
            return self.env["hr.employee"]
        return lookup(record)

    def _send_push(self, device, title, body):
        if not requests:
            _logger.warning("deployfleet_mobile_push_bridge: 'requests' not installed, cannot send push.")
            return
        try:
            requests.post(
                _EXPO_PUSH_URL,
                json={"to": device.push_token, "title": title, "body": body},
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001 — a failed push must never break event dispatch
            _logger.warning("deployfleet_mobile_push_bridge: push to %s failed: %s", device.push_token, exc)
