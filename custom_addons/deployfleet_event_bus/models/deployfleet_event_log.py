import fnmatch
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class DeployfleetEventLog(models.Model):
    """The DeployFleet event bus.

    Unlike the DeployGuard source this was ported from, dispatch does not
    hardcode a fixed list of subscriber models — see
    `deployfleet.event.subscription` for the registry that replaces it
    (docs/architecture/06-risks-and-recommendations.md risk #4).
    """

    _name = "deployfleet.event.log"
    _description = "DeployFleet Event Bus Log"
    _order = "create_date desc, id desc"

    name = fields.Char(
        required=True,
        index=True,
        string="Event Name",
        help="System-wide event identifier, e.g. 'vehicle.breakdown.created', 'trip.delayed'.",
    )
    source_model = fields.Char(required=True, index=True)
    source_id = fields.Integer(required=True, index=True)
    event_data = fields.Text(string="Event JSON Payload")
    state = fields.Selection(
        [("draft", "Draft"), ("processed", "Processed"), ("failed", "Failed")],
        default="draft",
        required=True,
        index=True,
    )
    error_message = fields.Text()

    @api.model
    def register_event(self, name, source_model, source_id, payload=None, **kwargs):
        """Primary API to publish an event onto the bus. Creates an audit
        record and immediately dispatches it to every registered subscriber
        whose pattern matches `name`."""
        data = payload if payload is not None else (kwargs or None)
        data_str = ""
        if data:
            try:
                data_str = json.dumps(data)
            except (TypeError, ValueError) as exc:
                _logger.warning("deployfleet_event_bus: could not serialize payload for %s: %s", name, exc)

        # Publishing an event must succeed regardless of the calling
        # user's role — deployfleet.event.log grants create/write to
        # base.group_system only, and no DeployFleet role implies it.
        # Every unsudo'd call site (dispatch confirm/cancel, trip
        # depart/complete/delay, delivery creation, vehicle status
        # changes, invoice creation, maintenance recording) would raise
        # AccessError for every real dispatcher/manager/driver account
        # — the same bug shape already found and fixed once for the AI
        # pipeline's own config/budget/cache models. sudo() is scoped to
        # just this bookkeeping create, not propagated into dispatch:
        # rebinding back to the caller's own env below keeps
        # _dispatch_event()'s subscriber-handler invocations running as
        # the real calling user, unchanged — several subscribers (e.g.
        # the AI entity-summary cache invalidation) are already written
        # expecting that and apply their own sudo() only where they
        # specifically need to.
        log = self.sudo().create({
            "name": name,
            "source_model": source_model,
            "source_id": source_id,
            "event_data": data_str,
        }).with_env(self.env)
        log._dispatch_event()
        return log

    def _dispatch_event(self):
        self.ensure_one()
        payload = {}
        if self.event_data:
            try:
                payload = json.loads(self.event_data)
            except (TypeError, ValueError):
                payload = {}

        subscriptions = self.env["deployfleet.event.subscription"].search([("active", "=", True)])
        matching = subscriptions.filtered(lambda s: fnmatch.fnmatch(self.name, s.event_pattern))

        errors = []
        for sub in matching:
            if sub.model_name not in self.env:
                _logger.warning(
                    "deployfleet_event_bus: subscription %s references unknown model %s — skipping",
                    sub.display_name, sub.model_name,
                )
                continue
            handler = getattr(self.env[sub.model_name], sub.method_name, None)
            if handler is None:
                _logger.warning(
                    "deployfleet_event_bus: %s has no method %s — skipping",
                    sub.model_name, sub.method_name,
                )
                continue
            try:
                handler(self.name, self.source_model, self.source_id, payload)
            except Exception as exc:  # noqa: BLE001 — a failing subscriber must never break the publisher
                _logger.error(
                    "deployfleet_event_bus: subscriber %s.%s failed for event %s: %s",
                    sub.model_name, sub.method_name, self.name, exc,
                )
                errors.append(f"{sub.model_name}.{sub.method_name}: {exc}")

        # sudo()'d for the same reason as the create() in register_event()
        # — this bookkeeping write must succeed for every role, and is
        # scoped narrowly to just this write rather than the whole
        # dispatch loop above, which deliberately stays in the caller's
        # own env.
        if errors:
            self.sudo().write({"state": "failed", "error_message": "\n".join(errors)})
        else:
            self.sudo().write({"state": "processed"})
