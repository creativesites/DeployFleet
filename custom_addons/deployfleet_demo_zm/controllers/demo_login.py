import logging

from odoo import http
from odoo.exceptions import AccessDenied
from odoo.http import request

_logger = logging.getLogger(__name__)

# Role slug -> demo login (kept in sync with hooks.py's _create_demo_login_users,
# which is the only place these res.users records are ever created).
_ROLE_LOGINS = {
    "owner": "demo.owner@deployfleet.demo",
    "dispatcher": "demo.dispatcher@deployfleet.demo",
    "driver": "demo.driver@deployfleet.demo",
    "customer": "demo.customer@deployfleet.demo",
}


class DeployfleetDemoLoginController(http.Controller):
    """One-click demo login, consumed by the login page buttons
    deployfleet_ui adds to web.login. POST-only (this authenticates a
    session - a GET-triggered login would be bad HTTP semantics and
    crawler-triggerable). Gated end-to-end by
    deployfleet_demo_zm.demo_login_enabled, which is only ever set True
    by this module's own post_init_hook - a real customer database that
    never installed this demo/tooling-only module has no route, no demo
    users, and no config parameter to gate on, so this feature is
    structurally absent there, not merely hidden.
    """

    @http.route("/web/login/demo/<string:role>", type="http", auth="public", methods=["POST"], csrf=True)
    def demo_login(self, role, **_kw):
        icp = request.env["ir.config_parameter"].sudo()
        if icp.get_param("deployfleet_demo_zm.demo_login_enabled") != "True":
            return request.not_found()

        login = _ROLE_LOGINS.get(role)
        password = icp.get_param(f"deployfleet_demo_zm.demo_login_password_{role}") if login else None
        if not login or not password:
            return request.not_found()

        try:
            request.session.authenticate(request.env, {"type": "password", "login": login, "password": password})
        except AccessDenied:
            _logger.warning("deployfleet_demo_zm: demo login failed for role %r", role)
            return request.redirect("/web/login?error=access")

        return request.redirect("/odoo")
