from odoo import fields, models
from odoo.exceptions import UserError


class DeployfleetInsuranceClaim(models.Model):
    """A claim filed against an insurance policy."""

    _name = "deployfleet.insurance.claim"
    _description = "DeployFleet Insurance Claim"
    _order = "incident_date desc"

    policy_id = fields.Many2one("deployfleet.insurance.policy", required=True, ondelete="cascade")
    claim_number = fields.Char()
    incident_date = fields.Date(default=fields.Date.context_today, required=True)
    description = fields.Text()
    amount_claimed = fields.Monetary()
    amount_approved = fields.Monetary()
    currency_id = fields.Many2one(related="policy_id.currency_id", store=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("paid", "Paid"),
        ],
        default="draft", required=True,
    )

    def _check_state(self, expected):
        for claim in self:
            if claim.state != expected:
                raise UserError(
                    self.env._(
                        "Claim must be in state '%(expected)s' for this action, not '%(actual)s'.",
                        expected=expected, actual=claim.state,
                    )
                )

    def action_submit(self):
        self._check_state("draft")
        self.write({"state": "submitted"})

    def action_approve(self, amount_approved=None):
        self._check_state("submitted")
        for claim in self:
            claim.write({
                "state": "approved",
                "amount_approved": amount_approved if amount_approved is not None else claim.amount_claimed,
            })

    def action_reject(self):
        self._check_state("submitted")
        self.write({"state": "rejected"})

    def action_mark_paid(self):
        self._check_state("approved")
        self.write({"state": "paid"})
