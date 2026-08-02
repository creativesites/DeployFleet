from odoo import fields, models


class DeployfleetMobileDevice(models.Model):
    """A registered push-notification token for one of the three mobile
    apps' logged-in users. The device-token field existed unused in the
    DeployGuard source this was forked from (see
    docs/architecture/02-reuse-strategy.md §6) - this module is what
    actually wires it to something."""

    _name = "deployfleet.mobile.device"
    _description = "DeployFleet Mobile Push Device"
    _order = "create_date desc"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade", index=True)
    push_token = fields.Char(required=True, help="Expo push token, e.g. 'ExponentPushToken[...]'.")
    platform = fields.Selection([("ios", "iOS"), ("android", "Android")], required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("push_token_unique", "UNIQUE(push_token)", "This device token is already registered."),
    ]

    def _register(self, user, push_token, platform):
        existing = self.search([("push_token", "=", push_token)], limit=1)
        if existing:
            existing.write({"user_id": user.id, "platform": platform, "active": True})
            return existing
        return self.create({"user_id": user.id, "push_token": push_token, "platform": platform})
