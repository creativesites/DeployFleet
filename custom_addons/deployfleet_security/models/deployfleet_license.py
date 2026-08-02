from odoo import api, fields, models


class DeployfleetLicense(models.Model):
    _name = "deployfleet.license"
    _description = "DeployFleet Product License"
    _order = "create_date desc"

    name = fields.Char(required=True, default="DeployFleet License")
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company
    )
    license_key = fields.Char(required=True, copy=False)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("invalid", "Invalid"),
        ],
        default="draft",
        required=True,
        copy=False,
    )
    valid_until = fields.Date()
    max_users = fields.Integer(help="0 = unlimited")
    notes = fields.Text()
    log_ids = fields.One2many("deployfleet.license.log", "license_id", string="Activity Log")

    def _log(self, message):
        self.ensure_one()
        self.env["deployfleet.license.log"].create({
            "license_id": self.id,
            "message": message,
        })

    def action_activate(self):
        for record in self:
            if record.valid_until and record.valid_until < fields.Date.today():
                record.state = "expired"
                record._log("Activation attempted on an already-expired license.")
                continue
            record.state = "active"
            record._log("License activated.")

    def action_invalidate(self, reason=""):
        for record in self:
            record.state = "invalid"
            record._log(f"License invalidated. Reason: {reason}" if reason else "License invalidated.")

    @api.model
    def _cron_check_expiry(self):
        """Daily cron target: flip any active license past its valid_until to expired."""
        today = fields.Date.today()
        expiring = self.search([
            ("state", "=", "active"),
            ("valid_until", "!=", False),
            ("valid_until", "<", today),
        ])
        for record in expiring:
            record.state = "expired"
            record._log("License expired (automatic check).")
        return expiring

    def is_valid(self):
        self.ensure_one()
        if self.state != "active":
            return False
        if self.valid_until and self.valid_until < fields.Date.today():
            return False
        return True


class DeployfleetLicenseLog(models.Model):
    _name = "deployfleet.license.log"
    _description = "DeployFleet License Activity Log"
    _order = "create_date desc"

    license_id = fields.Many2one("deployfleet.license", required=True, ondelete="cascade")
    message = fields.Char(required=True)
