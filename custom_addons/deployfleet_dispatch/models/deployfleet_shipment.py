from odoo import api, fields, models
from odoo.exceptions import UserError


class DeployfleetShipment(models.Model):
    """The cargo/load record — see docs/architecture/09-dispatch-module-design.md
    §2 for why this exists as its own entity rather than folding cargo
    details into the trip record (per review: "a trip without cargo is
    meaningless").

    `state` includes `in_transit`/`delivered` even though nothing in this
    module sets them — `deployfleet_trip` and `deployfleet_delivery`
    (built next) advance the shipment into those states as events fire, so
    the enum is defined once here rather than migrated later.
    """

    _name = "deployfleet.shipment"
    _description = "DeployFleet Shipment"
    _order = "create_date desc"
    _inherit = ["deployfleet.sequence.mixin"]

    name = fields.Char(required=True, copy=False, default="New")
    customer_id = fields.Many2one("res.partner", required=True)
    contract_id = fields.Many2one(
        "deployfleet.contract",
        help="Optional — a shipment with no contract is a spot load, not an error state. "
             "See docs/architecture/07-domain-model-erd.md §3.",
    )
    cargo_description = fields.Char()
    weight_kg = fields.Float()
    pickup_depot_id = fields.Many2one("deployfleet.depot", required=True, string="Pickup")
    dropoff_depot_id = fields.Many2one("deployfleet.depot", required=True, string="Drop-off")
    requested_pickup_date = fields.Datetime()
    required_vehicle_type_id = fields.Many2one(
        "deployfleet.vehicle.type",
        help="Leave empty if any vehicle type is acceptable for this shipment.",
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("confirmed", "Confirmed"),
            ("assigned", "Assigned"),
            ("in_transit", "In Transit"),
            ("delivered", "Delivered"),
            ("cancelled", "Cancelled"),
        ],
        default="draft",
        required=True,
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    assignment_ids = fields.One2many("deployfleet.dispatch.assignment", "shipment_id", string="Dispatch Assignments")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self._deployfleet_next_reference("deployfleet.shipment")
        return super().create(vals_list)

    @api.constrains("pickup_depot_id", "dropoff_depot_id")
    def _check_pickup_dropoff_differ(self):
        for shipment in self:
            if shipment.pickup_depot_id == shipment.dropoff_depot_id:
                raise UserError(self.env._("Pickup and drop-off depots must be different."))

    def action_confirm(self):
        for shipment in self:
            if shipment.state != "draft":
                continue
            shipment.state = "confirmed"

    def action_cancel(self):
        for shipment in self:
            shipment.assignment_ids.filtered(lambda a: a.state in ("draft", "proposed", "confirmed")).action_cancel()
            shipment.state = "cancelled"

    # ------------------------------------------------------------------
    # Scoring engine — see docs/architecture/09-dispatch-module-design.md §4.
    # Deliberately a simple weighted heuristic for Phase 1, not a solver.
    # ------------------------------------------------------------------

    def _driver_has_conflicting_assignment(self, driver):
        self.ensure_one()
        if not self.requested_pickup_date:
            return False
        return bool(self.env["deployfleet.dispatch.assignment"].search_count([
            ("driver_id", "=", driver.id),
            ("state", "in", ("proposed", "confirmed")),
            ("shipment_id.requested_pickup_date", "=", self.requested_pickup_date),
            ("shipment_id", "!=", self.id),
        ]))

    def _score_candidate(self, vehicle, driver):
        """Returns None to hard-disqualify a (vehicle, driver) pair, or a
        float score otherwise (higher is better). The two hard
        disqualifiers here (vehicle availability, vehicle-type
        qualification) are also the hook point Phase 3's
        deployfleet_dispatch_compliance will extend with document-expiry
        and rest-hour checks — same mechanism, another early return."""
        self.ensure_one()
        if vehicle.status != "available":
            return None
        if self.required_vehicle_type_id and vehicle.vehicle_type_id != self.required_vehicle_type_id:
            return None
        if self._driver_has_conflicting_assignment(driver):
            return None

        score = 100.0
        score += min(driver.deployfleet_years_experience, 10) * 2.0
        score -= driver.deployfleet_accident_count * 5.0
        return score

    def action_suggest_assignments(self, limit=3):
        """Scores every available (vehicle, driver) pair and creates
        `proposed` dispatch assignments for the top `limit` candidates."""
        self.ensure_one()
        assignment_model = self.env["deployfleet.dispatch.assignment"]
        self.assignment_ids.filtered(lambda a: a.state == "proposed").unlink()

        vehicles = self.env["deployfleet.vehicle"].search([("status", "=", "available")])
        drivers = self.env["hr.employee"].search([("deployfleet_is_driver", "=", True)])

        candidates = []
        for vehicle in vehicles:
            for driver in drivers:
                score = self._score_candidate(vehicle, driver)
                if score is not None:
                    candidates.append((score, vehicle, driver))
        candidates.sort(key=lambda c: c[0], reverse=True)

        created = assignment_model.browse()
        for score, vehicle, driver in candidates[:limit]:
            created |= assignment_model.create({
                "shipment_id": self.id,
                "vehicle_id": vehicle.id,
                "driver_id": driver.id,
                "score": score,
                "state": "proposed",
                "planned_departure": self.requested_pickup_date,
            })
        return created
