from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

TYRE_POSITIONS = [
    ("front_left", "Front Left"),
    ("front_right", "Front Right"),
    ("rear_left_outer", "Rear Left Outer"),
    ("rear_left_inner", "Rear Left Inner"),
    ("rear_right_outer", "Rear Right Outer"),
    ("rear_right_inner", "Rear Right Inner"),
    ("spare", "Spare"),
]


class DeployfleetTyre(models.Model):
    """A physical tyre fitted to a vehicle position — see
    docs/architecture/04-module-structure.md: 'tread depth readings,
    position tracking, rotation/retread/scrap history.'
    """

    _name = "deployfleet.tyre"
    _description = "DeployFleet Tyre"
    _order = "vehicle_id, position"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    part_id = fields.Many2one(
        "deployfleet.part", help="The tyre product consumed from stock when this record was fitted.",
    )
    position = fields.Selection(TYRE_POSITIONS, required=True)
    serial_number = fields.Char()
    fitted_date = fields.Date(default=fields.Date.context_today, required=True)
    tread_depth_mm = fields.Float()
    state = fields.Selection(
        [("fitted", "Fitted"), ("retreaded", "Retreaded"), ("scrapped", "Scrapped")],
        default="fitted", required=True,
    )
    reading_ids = fields.One2many("deployfleet.tyre.reading", "tyre_id")
    event_ids = fields.One2many("deployfleet.tyre.event", "tyre_id")

    @api.constrains("vehicle_id", "position", "state")
    def _check_one_active_tyre_per_position(self):
        # Scrapped tyres are kept for history and must not block a
        # replacement tyre being recorded at the same (vehicle, position)
        # — only "fitted"/"retreaded" tyres compete for a position.
        for tyre in self:
            if tyre.state == "scrapped":
                continue
            conflicting = self.search([
                ("vehicle_id", "=", tyre.vehicle_id.id),
                ("position", "=", tyre.position),
                ("state", "!=", "scrapped"),
                ("id", "!=", tyre.id),
            ])
            if conflicting:
                raise ValidationError(
                    self.env._(
                        "%(vehicle)s already has an active tyre at %(position)s — "
                        "scrap or rotate the existing one first.",
                        vehicle=tyre.vehicle_id.display_name, position=tyre.position,
                    )
                )

    def action_record_reading(self, tread_depth_mm, odometer=None):
        self.ensure_one()
        self.env["deployfleet.tyre.reading"].create({
            "tyre_id": self.id, "tread_depth_mm": tread_depth_mm, "odometer": odometer or 0.0,
        })
        self.tread_depth_mm = tread_depth_mm

    def action_rotate(self, new_position):
        self.ensure_one()
        if self.state != "fitted":
            raise UserError(self.env._("Only a fitted tyre can be rotated."))
        self.env["deployfleet.tyre.event"].create({
            "tyre_id": self.id, "event_type": "rotation",
            "from_position": self.position, "to_position": new_position,
        })
        self.position = new_position

    def action_retread(self):
        for tyre in self:
            if tyre.state != "fitted":
                raise UserError(self.env._("Only a fitted tyre can be retreaded."))
            self.env["deployfleet.tyre.event"].create({"tyre_id": tyre.id, "event_type": "retread"})
            tyre.state = "retreaded"

    def action_scrap(self):
        for tyre in self:
            if tyre.state == "scrapped":
                raise UserError(self.env._("This tyre is already scrapped."))
            self.env["deployfleet.tyre.event"].create({"tyre_id": tyre.id, "event_type": "scrap"})
            tyre.state = "scrapped"
