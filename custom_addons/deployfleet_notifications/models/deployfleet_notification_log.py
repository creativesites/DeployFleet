import fnmatch
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

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


class DeployfleetNotificationLog(models.Model):
    """The event-bus handler for every `deployfleet.notification.rule`, and
    the audit trail of what was actually sent. Subscribed once, generically,
    to `deployfleet.*` (see data/deployfleet_notification_rule_data.xml's
    companion subscription) - matching against individual rules is this
    module's own concern, not the event bus's, so adding a notification
    never means adding another event_bus subscription record."""

    _name = "deployfleet.notification.log"
    _description = "DeployFleet Notification Log"
    _order = "create_date desc"

    rule_id = fields.Many2one("deployfleet.notification.rule", required=True, ondelete="cascade")
    event_name = fields.Char(required=True)
    source_model = fields.Char(required=True)
    source_id = fields.Integer(required=True)
    recipient_partner_id = fields.Many2one("res.partner", required=True)
    message = fields.Char(required=True)
    state = fields.Selection([("sent", "Sent"), ("failed", "Failed")], required=True)
    error_message = fields.Text()

    @api.model
    def _handle_bus_event(self, event_name, source_model, source_id, payload):
        rules = self.env["deployfleet.notification.rule"].search([("active", "=", True)])
        matching = rules.filtered(lambda rule: fnmatch.fnmatch(event_name, rule.event_pattern))
        for rule in matching:
            recipients = self._resolve_recipients(rule.recipient_type, source_model, source_id)
            for partner in recipients:
                self._notify_one(rule, event_name, source_model, source_id, payload, partner)

    def _notify_one(self, rule, event_name, source_model, source_id, payload, partner):
        try:
            message = rule.message_template.format(**(payload or {}))
        except (KeyError, IndexError):
            message = rule.name
        try:
            partner.message_post(body=message, subject=rule.name)
            state, error_message = "sent", False
        except Exception as exc:  # noqa: BLE001 — a failed notification must never break event dispatch
            _logger.error("deployfleet_notifications: failed to notify %s: %s", partner.display_name, exc)
            state, error_message = "failed", str(exc)
        self.create({
            "rule_id": rule.id,
            "event_name": event_name,
            "source_model": source_model,
            "source_id": source_id,
            "recipient_partner_id": partner.id,
            "message": message,
            "state": state,
            "error_message": error_message,
        })

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
