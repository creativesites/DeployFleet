from odoo import api, fields, models

ANOMALY_THRESHOLD_MULTIPLIER = 1.3


class DeployfleetFuelLog(models.Model):
    """A single fuel fill-up record — see
    docs/architecture/05-implementation-roadmap.md Phase 2: 'fuel logs,
    consumption analytics, and the first real AI hook... even a simple
    threshold rule is worth shipping before the predictive version lands
    in Phase 5.'

    `is_anomaly` is exactly that simple threshold rule: this fill-up's
    consumption compared against this vehicle's own trailing average,
    not an ML model. Deliberately does not depend on
    deployfleet_freight_calculator — fuel logging has value as a
    standalone record independent of the cost-estimation engine.
    """

    _name = "deployfleet.fuel.log"
    _description = "DeployFleet Fuel Log"
    _order = "date desc, id desc"

    # Engineering-audit fix (C-01): no company_id field existed on this
    # model at all.
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    vehicle_id = fields.Many2one("deployfleet.vehicle", required=True)
    driver_id = fields.Many2one("hr.employee", domain=[("deployfleet_is_driver", "=", True)])
    date = fields.Date(default=fields.Date.context_today, required=True)
    odometer = fields.Float(required=True, help="Odometer reading at this fill-up.")
    liters = fields.Float(required=True)
    total_cost = fields.Monetary()
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id)
    distance_since_last_km = fields.Float(compute="_compute_consumption", store=True)
    consumption_l_per_100km = fields.Float(compute="_compute_consumption", store=True)
    is_anomaly = fields.Boolean(
        compute="_compute_consumption", store=True,
        help="Consumption more than 30% above this vehicle's own trailing average.",
    )

    def _previous_log(self):
        self.ensure_one()
        return self.search([
            ("vehicle_id", "=", self.vehicle_id.id),
            ("id", "!=", self.id),
            ("date", "<=", self.date),
        ], order="date desc, id desc", limit=1)

    @api.depends("vehicle_id", "date", "odometer", "liters")
    def _compute_consumption(self):
        for log in self:
            previous = log._previous_log()
            distance = log.odometer - previous.odometer if previous else 0.0
            log.distance_since_last_km = distance
            log.consumption_l_per_100km = (log.liters / distance * 100) if distance > 0 else 0.0

            prior_logs = self.search([
                ("vehicle_id", "=", log.vehicle_id.id),
                ("id", "!=", log.id),
                ("consumption_l_per_100km", ">", 0),
            ])
            if prior_logs and log.consumption_l_per_100km:
                average = sum(prior_logs.mapped("consumption_l_per_100km")) / len(prior_logs)
                log.is_anomaly = log.consumption_l_per_100km > average * ANOMALY_THRESHOLD_MULTIPLIER
            else:
                log.is_anomaly = False
