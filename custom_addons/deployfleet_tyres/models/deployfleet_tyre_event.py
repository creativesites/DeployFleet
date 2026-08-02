from odoo import fields, models

from .deployfleet_tyre import TYRE_POSITIONS


class DeployfleetTyreEvent(models.Model):
    """The rotation/retread/scrap history for one tyre. `from_position`/
    `to_position` are stored (not related to `tyre_id.position`) because
    they must capture the position at the time of the event, not the
    tyre's current position — a related field would silently show the
    wrong value for every past rotation once the tyre moves again."""

    _name = "deployfleet.tyre.event"
    _description = "DeployFleet Tyre Event"
    _order = "date desc, id desc"

    tyre_id = fields.Many2one("deployfleet.tyre", required=True, ondelete="cascade")
    date = fields.Date(default=fields.Date.context_today, required=True)
    event_type = fields.Selection(
        [("rotation", "Rotation"), ("retread", "Retread"), ("scrap", "Scrap")],
        required=True,
    )
    from_position = fields.Selection(TYRE_POSITIONS, help="Only set for rotation events.")
    to_position = fields.Selection(TYRE_POSITIONS, help="Only set for rotation events.")
