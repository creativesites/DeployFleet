from odoo import api, fields, models


class HrEmployee(models.Model):
    """Driver profile fields. Per docs/architecture/04-module-structure.md,
    a driver is not just an employee with a few extra fields the way a
    DeployGuard guard arguably was — license class, endorsements, vehicle-
    type qualifications, and a risk profile are substantial enough to
    warrant their own module, even though they still live on hr.employee
    via classical _inherit (an employee genuinely *is* one record; there's
    no "separate owned table" question here the way there was for vehicle).

    Deviation from docs/architecture/04-module-structure.md worth recording:
    that document lists a `deployfleet_hr` module as this one's dependency,
    for "general staff administration for non-driver roles." It isn't built
    — there's no content for it yet (dispatchers/mechanics/admin currently
    need nothing beyond stock hr.employee), and an empty module just to
    match a dependency diagram is exactly the premature abstraction
    CLAUDE.md warns against. Add it when a real non-driver-staff need shows
    up, not before.
    """

    _inherit = "hr.employee"

    deployfleet_is_driver = fields.Boolean(
        string="Is DeployFleet Driver",
        help="Flags this employee as a driver — dispatchers, managers, and other staff leave this unchecked.",
    )
    deployfleet_license_class = fields.Selection(
        [
            ("b", "Class B — Light Vehicle"),
            ("c1", "Class C1 — Medium Goods"),
            ("c", "Class C — Heavy Goods"),
            ("d1", "Class D1 — Minibus"),
            ("d", "Class D — Bus"),
            ("ce", "Class CE — Articulated / Trailer Combination"),
        ],
        string="License Class",
    )
    deployfleet_license_number = fields.Char(string="License Number")
    deployfleet_license_expiry = fields.Date(string="License Expiry")
    deployfleet_license_is_expired = fields.Boolean(
        compute="_compute_deployfleet_license_is_expired", string="License Expired"
    )
    deployfleet_endorsements = fields.Char(
        string="Endorsements", help="Free-text for Phase 1, e.g. 'Hazmat, Defensive Driving'."
    )
    deployfleet_qualified_vehicle_type_ids = fields.Many2many(
        "deployfleet.vehicle.type", string="Qualified Vehicle Types"
    )
    deployfleet_years_experience = fields.Integer(string="Years of Driving Experience")
    deployfleet_risk_score = fields.Float(
        string="Risk Score", default=100.0,
        help="100 = no known risk signal. Lowered by driver-performance incidents once "
             "deployfleet_driver_performance (Phase 3) is installed; manually adjustable until then.",
    )
    deployfleet_accident_count = fields.Integer(string="Recorded Accidents", default=0)

    @api.depends("deployfleet_license_expiry")
    def _compute_deployfleet_license_is_expired(self):
        today = fields.Date.today()
        for employee in self:
            employee.deployfleet_license_is_expired = bool(
                employee.deployfleet_license_expiry and employee.deployfleet_license_expiry < today
            )
