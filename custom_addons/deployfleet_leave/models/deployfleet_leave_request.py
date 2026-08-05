from datetime import datetime, time

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class DeployfleetLeaveRequest(models.Model):
    """A leave request — approving one checks for scheduled trips during
    the requested period, which is why this module depends on
    deployfleet_trip rather than being a pure HR-only feature.
    """

    _name = "deployfleet.leave.request"
    _description = "DeployFleet Leave Request"
    _order = "date_from desc"

    employee_id = fields.Many2one("hr.employee", required=True)
    leave_type_id = fields.Many2one("deployfleet.leave.type", required=True)
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    number_of_days = fields.Float(compute="_compute_number_of_days", store=True)
    reason = fields.Text()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True,
    )

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for request in self:
            if request.date_to < request.date_from:
                raise ValidationError(self.env._("The end date must not be before the start date."))

    @api.depends("date_from", "date_to")
    def _compute_number_of_days(self):
        for request in self:
            if request.date_from and request.date_to:
                request.number_of_days = (request.date_to - request.date_from).days + 1
            else:
                request.number_of_days = 0.0

    def _check_state(self, expected):
        for request in self:
            if request.state != expected:
                raise UserError(
                    self.env._(
                        "Leave request must be in state '%(expected)s' for this action, not '%(actual)s'.",
                        expected=expected, actual=request.state,
                    )
                )

    def action_submit(self):
        self._check_state("draft")
        self.write({"state": "submitted"})

    def _check_can_decide(self):
        if not self.env.user.has_group("deployfleet_security.group_deployfleet_dispatcher"):
            raise UserError(self.env._("Only a dispatcher, manager, or owner may approve or reject a leave request."))

    def action_approve(self):
        self._check_state("submitted")
        self._check_can_decide()
        for request in self:
            conflicting_trips = self.env["deployfleet.trip"].search([
                ("driver_id", "=", request.employee_id.id),
                ("state", "in", ("planned", "departed")),
                ("planned_departure", ">=", datetime.combine(request.date_from, time.min)),
                ("planned_departure", "<=", datetime.combine(request.date_to, time.max)),
            ])
            if conflicting_trips:
                raise UserError(
                    self.env._(
                        "Cannot approve leave — %(count)s trip(s) are scheduled for this employee "
                        "during the requested period.",
                        count=len(conflicting_trips),
                    )
                )
            request.state = "approved"

    def action_reject(self):
        self._check_state("submitted")
        self._check_can_decide()
        self.write({"state": "rejected"})

    def action_cancel(self):
        for request in self:
            if request.state not in ("draft", "submitted", "approved"):
                raise UserError(self.env._("This leave request cannot be cancelled from its current state."))
            request.state = "cancelled"
