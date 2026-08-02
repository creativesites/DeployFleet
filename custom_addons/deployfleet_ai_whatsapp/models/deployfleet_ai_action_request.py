import json
import logging

from odoo import api, models

try:
    import requests
except ImportError:  # pragma: no cover — declared in __manifest__.py external_dependencies
    requests = None

_logger = logging.getLogger(__name__)

_GRAPH_API_VERSION = "v19.0"
_BREAKDOWN_KEYWORD = "breakdown"


class DeployfleetAIActionRequest(models.Model):
    """Extends deployfleet_ai_actions' request model with the WhatsApp
    intent this module supports: a driver texting the word "breakdown"
    creates a `pending_approval` request to mark their currently assigned
    vehicle as broken down - it never calls `action_approve()` itself, so
    the WhatsApp channel can propose a report but can never make it take
    effect on its own. See
    docs/architecture/08-ai-architecture.md §5's example: "a
    WhatsApp-reported breakdown creating a real ticket" - gated by the
    same non-negotiable human-approval pipeline as every other AI action.
    """

    _inherit = "deployfleet.ai.action.request"

    @api.model
    def _handle_whatsapp_message(self, config, from_phone, message_text):
        if _BREAKDOWN_KEYWORD not in (message_text or "").lower():
            return None

        driver = self._find_driver_by_phone(from_phone)
        if not driver:
            self._send_whatsapp_reply(
                config, from_phone,
                "We could not match your number to a registered driver. Please contact dispatch directly.",
            )
            return None

        vehicle = self.env["deployfleet.vehicle"].search([("current_driver_id", "=", driver.id)], limit=1)
        if not vehicle:
            self._send_whatsapp_reply(
                config, from_phone,
                "No vehicle is currently assigned to you. Please contact dispatch directly.",
            )
            return None

        feature = self.env["deployfleet.ai.feature"].search(
            [("key", "=", "whatsapp_breakdown_report")], limit=1
        )
        action_request = self.create({
            "feature_id": feature.id,
            "action_type": "report_vehicle_breakdown",
            "target_model": "deployfleet.vehicle",
            "target_id": vehicle.id,
            "proposed_vals": json.dumps({"status": "breakdown"}),
            "source_context": "whatsapp_message",
        })
        action_request.action_submit_for_approval()
        self._send_whatsapp_reply(
            config, from_phone,
            "Your breakdown report has been received and is pending dispatcher approval.",
        )
        return action_request

    @api.model
    def _find_driver_by_phone(self, from_phone):
        digits = "".join(ch for ch in (from_phone or "") if ch.isdigit())
        if len(digits) < 9:
            return self.env["hr.employee"]
        suffix = digits[-9:]
        drivers = self.env["hr.employee"].search([("deployfleet_is_driver", "=", True)])
        return drivers.filtered(
            lambda emp: emp.mobile_phone and "".join(ch for ch in emp.mobile_phone if ch.isdigit()).endswith(suffix)
        )[:1]

    @api.model
    def _send_whatsapp_reply(self, config, to_phone, body):
        if not requests:
            _logger.warning("deployfleet_ai_whatsapp: 'requests' not installed, cannot send reply.")
            return
        try:
            requests.post(
                f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{config.phone_number_id}/messages",
                headers={"Authorization": f"Bearer {config.access_token}", "Content-Type": "application/json"},
                json={"messaging_product": "whatsapp", "to": to_phone, "text": {"body": body}},
                timeout=10,
            )
        except Exception as exc:  # noqa: BLE001 — a failed reply must never break webhook handling
            _logger.warning("deployfleet_ai_whatsapp: reply to %s failed: %s", to_phone, exc)
