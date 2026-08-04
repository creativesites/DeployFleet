import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _tool_get_vehicle_summary(env, arguments):
    vehicle_id = arguments.get("vehicle_id")
    if not vehicle_id:
        return {"error": "vehicle_id is required."}
    vehicle = env["deployfleet.vehicle"].sudo().browse(int(vehicle_id))
    if not vehicle.exists():
        return {"error": f"No vehicle found with id {vehicle_id}."}
    return {
        "id": vehicle.id,
        "license_plate": vehicle.license_plate,
        "status": vehicle.status,
        "vehicle_type": vehicle.vehicle_type_id.name or None,
        "current_driver": vehicle.current_driver_id.name or None,
        "odometer": vehicle.odometer,
    }


def _tool_get_due_maintenance(env, _arguments):
    schedules = env["deployfleet.maintenance.schedule"].sudo().search(
        [("is_due", "=", True)], order="next_due_date asc", limit=20,
    )
    return {
        "count": len(schedules),
        "schedules": [
            {
                "id": schedule.id,
                "name": schedule.name,
                "vehicle": schedule.vehicle_id.license_plate or schedule.vehicle_id.display_name,
                "next_due_date": fields.Date.to_string(schedule.next_due_date) if schedule.next_due_date else None,
            }
            for schedule in schedules
        ],
    }


def _tool_get_available_drivers(env, arguments):
    """Driver availability is derived, not stored (confirmed by reading
    deployfleet_dispatch_compliance's own _driver_on_approved_leave() —
    there is no single boolean "driver status" field anywhere in the
    domain). Mirrors that same query shape rather than inventing a new
    availability definition."""
    target_date = arguments.get("date")
    drivers = env["hr.employee"].sudo().search([
        ("deployfleet_is_driver", "=", True),
        ("deployfleet_license_is_expired", "=", False),
    ])
    if target_date:
        on_leave_employee_ids = env["deployfleet.leave.request"].sudo().search([
            ("employee_id", "in", drivers.ids),
            ("state", "=", "approved"),
            ("date_from", "<=", target_date),
            ("date_to", ">=", target_date),
        ]).employee_id.ids
        drivers = drivers.filtered(lambda driver: driver.id not in on_leave_employee_ids)
    return {
        "count": len(drivers),
        "drivers": [
            {
                "id": driver.id,
                "name": driver.name,
                "license_class": driver.deployfleet_license_class,
                "years_experience": driver.deployfleet_years_experience,
            }
            for driver in drivers[:20]
        ],
    }


def _tool_get_unassigned_shipments(env, _arguments):
    shipments = env["deployfleet.shipment"].sudo().search(
        [("state", "=", "confirmed")], order="requested_pickup_date asc", limit=20,
    )
    return {
        "count": len(shipments),
        "shipments": [
            {
                "id": shipment.id,
                "customer": shipment.customer_id.name or None,
                "requested_pickup_date": (
                    fields.Datetime.to_string(shipment.requested_pickup_date)
                    if shipment.requested_pickup_date else None
                ),
            }
            for shipment in shipments
        ],
    }


def _tool_get_expiring_documents(env, _arguments):
    documents = env["deployfleet.compliance.document"].sudo().search(
        [("state", "in", ("expiring_soon", "expired"))], order="expiry_date asc", limit=20,
    )
    return {
        "count": len(documents),
        "documents": [
            {
                "id": document.id,
                "document_type": document.document_type_id.name or None,
                "state": document.state,
                "expiry_date": fields.Date.to_string(document.expiry_date) if document.expiry_date else None,
                "owner_model": document.res_model,
                "owner_id": document.res_id,
            }
            for document in documents
        ],
    }


# Fixed dispatch table, keyed by deployfleet.ai.tool.key — see the model
# docstring below for why this is dict-dispatch rather than dynamic
# getattr(model, method_name): a tool key is ultimately LLM-selected
# input, so the actual code path must stay fully static.
_TOOL_HANDLERS = {
    "get_vehicle_summary": _tool_get_vehicle_summary,
    "get_due_maintenance": _tool_get_due_maintenance,
    "get_available_drivers": _tool_get_available_drivers,
    "get_unassigned_shipments": _tool_get_unassigned_shipments,
    "get_expiring_documents": _tool_get_expiring_documents,
}


class DeployfleetAITool(models.Model):
    """A named, LLM-callable tool — docs/architecture/
    21-copilot-rail-architecture.md §3. Execution is dispatched through
    the fixed `_TOOL_HANDLERS` dict above, keyed by `key`, never by
    dynamic getattr(model, method_name) — tool keys are ultimately
    LLM-selected input (the provider picks which tool to call), so the
    actual code path stays fully static regardless of what the model
    proposes. `model_name`/`method_name` are kept as informational/
    documentation fields only, not the real execution path.

    This is the opposite security shape from
    deployfleet.ai.action.request's forbidden-model denylist: that
    pipeline's target is genuinely dynamic (any model/method an approver
    signs off on), so it's opt-out deny-list by construction. A tool's
    target is fixed at module-install time, so it's opt-in allow-list by
    construction — only entries in this table, with a handler that
    actually exists, are ever offered to a provider at all.
    """

    _name = "deployfleet.ai.tool"
    _description = "DeployFleet AI Tool (function/tool-calling registry)"
    _order = "sequence, id"

    key = fields.Char(
        required=True, index=True,
        help="Stable identifier passed to the provider as the tool's name, e.g. 'get_vehicle_summary'.",
    )
    name = fields.Char(required=True)
    description = fields.Text(
        required=True,
        help="Passed to the provider as the tool's description — what it does and when to call it.",
    )
    parameters_schema = fields.Text(
        default='{"type": "object", "properties": {}}',
        help="JSON Schema for this tool's arguments, passed to the provider as-is.",
    )
    read_only = fields.Boolean(
        default=True,
        help="Read tools execute immediately and always. Write tools are subject to §4's "
             "action-approval/auto-executable tiering instead of running directly.",
    )
    model_name = fields.Char(
        help="Informational only — documents which model this tool primarily reads/writes. "
             "Not the execution path; see _TOOL_HANDLERS in this file.",
    )
    method_name = fields.Char(
        help="Informational only — documents which method/handler this tool calls. "
             "Not the execution path; see _TOOL_HANDLERS in this file.",
    )
    agent_ids = fields.Many2many("deployfleet.ai.agent", string="Available to agents")
    sequence = fields.Integer(default=10)

    _sql_constraints = [
        ("key_unique", "UNIQUE(key)", "Tool key must be unique."),
    ]

    @api.constrains("key")
    def _check_key_has_handler(self):
        for tool in self:
            if tool.key not in _TOOL_HANDLERS:
                raise UserError(self.env._(
                    "Tool key '%(key)s' has no registered handler in _TOOL_HANDLERS — "
                    "a deployfleet.ai.tool record must name a key this module's code actually "
                    "implements, never an arbitrary model/method pair.",
                    key=tool.key,
                ))

    def to_llm_schema(self):
        """Returns this tool's {"name", "description", "parameters"} dict —
        the shape deployfleet.ai.core.complete_with_tools() expects in its
        `tools` list."""
        self.ensure_one()
        try:
            parameters = json.loads(self.parameters_schema or "{}")
        except ValueError:
            parameters = {"type": "object", "properties": {}}
        return {"name": self.key, "description": self.description, "parameters": parameters}

    def execute(self, arguments):
        """Runs this tool's handler via the fixed dispatch table. Never
        raises — an unknown key or a handler exception both become an
        {"error": ...} dict so a bad tool call degrades to something the
        model can react to, rather than aborting the whole chat turn."""
        self.ensure_one()
        handler = _TOOL_HANDLERS.get(self.key)
        if not handler:
            return {"error": f"Tool '{self.key}' has no registered handler."}
        try:
            return handler(self.env, arguments or {})
        except Exception as exc:  # noqa: BLE001 — feed failures back to the model, don't crash the chat turn
            _logger.exception("deployfleet.ai.tool '%s' handler raised", self.key)
            return {"error": str(exc)}

    @api.model
    def schemas_for_agent(self, agent):
        """LLM-facing tool schemas for every tool this agent may call."""
        tools = self.search([("agent_ids", "=", agent.id)])
        return [tool.to_llm_schema() for tool in tools]

    @api.model
    def build_executor(self, agent):
        """Returns a callable(name, arguments) -> result bound to this
        agent's available tools — the shape deployfleet.ai.core.
        complete_with_tools()'s `executor` parameter expects. A tool-call
        for a key not in this agent's own tool set is refused, not
        silently run against some other agent's tool — an agent's tool
        set (§3's `agent_ids`) is itself part of the access boundary this
        registry exists to enforce."""
        tools_by_key = {tool.key: tool for tool in self.search([("agent_ids", "=", agent.id)])}

        def executor(name, arguments):
            tool = tools_by_key.get(name)
            if not tool:
                return {"error": f"Tool '{name}' is not available to this agent."}
            return tool.execute(arguments)

        return executor
