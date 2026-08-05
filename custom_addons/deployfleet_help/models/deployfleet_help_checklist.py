from odoo import fields, models


class DeployfleetHelpChecklist(models.Model):
    """A first-time-setup checklist ("First-Time Setup" is the only
    record seeded today) — modeled as real data rather than hardcoded
    UI, so a future role-specific checklist is just a new record, not
    a code change."""

    _name = "deployfleet.help.checklist"
    _description = "DeployFleet Help Checklist"
    _order = "sequence, name"

    name = fields.Char(required=True)
    description = fields.Char()
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    item_ids = fields.One2many("deployfleet.help.checklist.item", "checklist_id")


class DeployfleetHelpChecklistItem(models.Model):
    _name = "deployfleet.help.checklist.item"
    _description = "DeployFleet Help Checklist Item"
    _order = "sequence"

    checklist_id = fields.Many2one("deployfleet.help.checklist", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)
    title = fields.Char(required=True)
    description = fields.Char()
    action_xml_id = fields.Char(help="The ir.actions.client/act_window XML ID the item's 'Do this' button opens.")
    icon = fields.Char(help="FontAwesome class.")
    related_article_id = fields.Many2one("deployfleet.help.article", help="'Learn more' link.")
