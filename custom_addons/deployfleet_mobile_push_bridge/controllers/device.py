from odoo import http
from odoo.addons.deployfleet_core.controllers.mobile_api import (
    envelope_error,
    envelope_success,
    require_authenticated,
)
from odoo.http import request


class DeployfleetMobileDeviceController(http.Controller):
    """Device-token registration for any of the three mobile apps - one
    endpoint shared by all of them, since registering a push token has
    nothing role-specific about it."""

    @http.route("/api/mobile/push/register", type="http", auth="user", methods=["POST"], csrf=False)
    @require_authenticated
    def register(self, push_token=None, platform=None, **_kw):
        if not push_token or platform not in ("ios", "android"):
            return request.make_json_response(
                envelope_error("push_token and platform ('ios' or 'android') are required.")
            )
        device = request.env["deployfleet.mobile.device"].sudo()._register(
            request.env.user, push_token, platform
        )
        return request.make_json_response(envelope_success({"id": device.id}))
