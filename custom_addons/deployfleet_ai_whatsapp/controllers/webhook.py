import json

from odoo import http
from odoo.http import request


class DeployfleetAIWhatsappWebhookController(http.Controller):
    """Meta WhatsApp Cloud API webhook. Turns an inbound "breakdown"
    report into a `deployfleet.ai.action.request` in `pending_approval`
    state and nothing more - it never calls `action_approve()` itself, so
    a WhatsApp message can never execute a write on its own, per
    docs/architecture/08-ai-architecture.md §5's non-negotiable
    human-approval gate. See README.rst for the signature-verification
    gap this controller does not yet close.
    """

    @http.route("/api/whatsapp/webhook", type="http", auth="public", methods=["GET"], csrf=False)
    def verify_webhook(self, **params):
        mode = params.get("hub.mode")
        token = params.get("hub.verify_token")
        challenge = params.get("hub.challenge", "")
        config = request.env["deployfleet.ai.whatsapp.config"].sudo().search([
            ("webhook_verify_token", "=", token), ("enabled", "=", True),
        ], limit=1)
        if mode == "subscribe" and config:
            return request.make_response(challenge)
        return request.make_response("Forbidden", status=403)

    @http.route("/api/whatsapp/webhook", type="http", auth="public", methods=["POST"], csrf=False)
    def receive_message(self, **_kw):
        # NOTE: Meta signs this payload (X-Hub-Signature-256); this
        # controller does not yet verify it - see README.rst. Do not treat
        # this endpoint as hardened against spoofed requests until that's
        # closed.
        try:
            payload = json.loads(request.httprequest.data or b"{}")
        except (TypeError, ValueError):
            return request.make_json_response({"status": "ignored"})

        message, from_phone = self._extract_message(payload)
        if not message or not from_phone:
            return request.make_json_response({"status": "ignored"})

        config = request.env["deployfleet.ai.whatsapp.config"].sudo().search(
            [("enabled", "=", True)], limit=1
        )
        if not config:
            return request.make_json_response({"status": "ignored"})

        request.env["deployfleet.ai.action.request"].sudo()._handle_whatsapp_message(
            config, from_phone, message
        )
        return request.make_json_response({"status": "ok"})

    def _extract_message(self, payload):
        try:
            value = payload["entry"][0]["changes"][0]["value"]
            message = value["messages"][0]
            return message.get("text", {}).get("body"), message.get("from")
        except (KeyError, IndexError, TypeError):
            return None, None
