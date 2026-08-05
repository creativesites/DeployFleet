from odoo import fields, models


class DeployfleetHelpChecklistProgress(models.Model):
    """Per-user completion tracking for a checklist item — a plain M2M
    on the user or the item can't carry the extra `done`/`done_date`
    state a real progress row needs, hence this through-model.

    Items are user-toggled ("Mark done"), not auto-detected from real
    data (e.g. "has this user created a vehicle yet?") — that inference
    would be real, useful, per-item-bespoke logic, and is a named
    future enhancement, not built here.
    """

    _name = "deployfleet.help.checklist.progress"
    _description = "DeployFleet Help Checklist Progress"

    user_id = fields.Many2one("res.users", required=True, default=lambda self: self.env.user)
    checklist_item_id = fields.Many2one("deployfleet.help.checklist.item", required=True, ondelete="cascade")
    done = fields.Boolean(default=False)
    done_date = fields.Datetime()

    _sql_constraints = [
        ("user_item_unique", "UNIQUE(user_id, checklist_item_id)", "Progress for this item is already tracked."),
    ]

    def action_toggle_done(self):
        for progress in self:
            progress.done = not progress.done
            progress.done_date = fields.Datetime.now() if progress.done else False
