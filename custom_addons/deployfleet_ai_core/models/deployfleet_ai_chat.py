from odoo import fields, models


class DeployfleetAIChatSession(models.Model):
    _name = "deployfleet.ai.chat.session"
    _description = "DeployFleet AI Assistant Chat Session"
    _order = "create_date desc"

    name = fields.Char(default="AI Chat")
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    message_ids = fields.One2many("deployfleet.ai.chat.message", "session_id")


class DeployfleetAIChatMessage(models.Model):
    _name = "deployfleet.ai.chat.message"
    _description = "DeployFleet AI Assistant Chat Message"
    _order = "create_date asc"

    session_id = fields.Many2one("deployfleet.ai.chat.session", required=True, ondelete="cascade")
    role = fields.Selection([("user", "User"), ("assistant", "Assistant")], required=True)
    content = fields.Text(required=True)
