from odoo import fields, models
from odoo.exceptions import UserError


class DeployfleetDispatchAssignment(models.Model):
    """The planning-time pairing of shipment + route + vehicle + driver.
    See docs/architecture/09-dispatch-module-design.md §3 for the workflow
    this implements. Deliberately a separate entity from the eventual trip
    record (built in deployfleet_trip) — the plan is auditable separately
    from what actually happened, the same distinction that made
    DeployGuard's roster-slot/attendance-record split valuable.
    """

    _name = "deployfleet.dispatch.assignment"
    _description = "DeployFleet Dispatch Assignment"
    _order = "create_date desc"

    shipment_id = fields.Many2one("deployfleet.shipment", required=True, ondelete="cascade")
    route_id = fields.Many2one(
        "deployfleet.route",
        help="Optional — ad hoc assignments need not reference a named route.",
    )
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    driver_id = fields.Many2one("hr.employee", required=True, domain=[("deployfleet_is_driver", "=", True)])
    planned_departure = fields.Datetime()
    planned_arrival = fields.Datetime()
    score = fields.Float(help="Output of deployfleet.shipment._score_candidate() at proposal time.")
    override_reason = fields.Char(
        help="Required to confirm this assignment if a higher-scored candidate is still proposed."
    )
    state = fields.Selection(
        [("draft", "Draft"), ("proposed", "Proposed"), ("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
        default="proposed",
        required=True,
    )

    def _higher_scored_siblings(self):
        self.ensure_one()
        return self.shipment_id.assignment_ids.filtered(
            lambda a: a.id != self.id and a.state == "proposed" and a.score > self.score
        )

    def _proposed_siblings(self):
        self.ensure_one()
        return self.shipment_id.assignment_ids.filtered(
            lambda a: a.id != self.id and a.state == "proposed"
        )

    def action_confirm(self):
        for assignment in self:
            higher_scored = assignment._higher_scored_siblings()
            if higher_scored and not assignment.override_reason:
                raise UserError(self.env._(
                    "A higher-scored candidate is available for this shipment. "
                    "Provide an override reason to confirm this assignment instead."
                ))

            assignment.state = "confirmed"
            assignment.vehicle_id.write({"status": "assigned", "current_driver_id": assignment.driver_id.id})
            assignment.shipment_id.state = "assigned"
            assignment._proposed_siblings().write({"state": "cancelled"})

            self.env["deployfleet.event.log"].register_event(
                "deployfleet.dispatch.assigned", "deployfleet.dispatch.assignment", assignment.id,
                {
                    "shipment_id": assignment.shipment_id.id,
                    "driver_id": assignment.driver_id.id,
                    "vehicle_id": assignment.vehicle_id.id,
                },
            )

    def action_cancel(self):
        for assignment in self:
            was_confirmed = assignment.state == "confirmed"
            assignment.state = "cancelled"
            if was_confirmed:
                assignment.vehicle_id.write({"status": "available", "current_driver_id": False})
                if assignment.shipment_id.state == "assigned":
                    assignment.shipment_id.state = "confirmed"

            self.env["deployfleet.event.log"].register_event(
                "deployfleet.dispatch.cancelled", "deployfleet.dispatch.assignment", assignment.id,
                {"shipment_id": assignment.shipment_id.id},
            )
