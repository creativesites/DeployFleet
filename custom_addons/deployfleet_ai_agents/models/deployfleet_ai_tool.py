import hashlib
import json
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


def _vehicle_summary_signature(vehicle):
    """Cheap fingerprint of the fields _vehicle_summary_text() actually
    reads - a change to any of them invalidates the cache on the next
    read, without needing a bus event for every possible field (doc 21
    §6's hybrid invalidation - see deployfleet.ai.entity.summary's own
    docstring in deployfleet_ai_core)."""
    raw = f"{vehicle.status}|{vehicle.current_driver_id.id}|{vehicle.odometer}|{vehicle.vehicle_type_id.id}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _vehicle_summary_text(vehicle):
    driver = vehicle.current_driver_id.name or "unassigned"
    vehicle_type = vehicle.vehicle_type_id.name or "unknown type"
    return (
        f"{vehicle.license_plate} ({vehicle_type}): status={vehicle.status}, "
        f"driver={driver}, odometer={vehicle.odometer} km"
    )


def _tool_get_vehicle_summary(env, arguments, _feature_key):
    """The one real consumer of deployfleet.ai.entity.summary (doc 21 §6,
    deployfleet_ai_core) - reads the cached summary_text when the
    vehicle's own source_signature still matches, recomputes and
    upserts it otherwise. The cache never replaces the live field read
    below (id/license_plate/status/... always come straight from the
    ORM record, never from the cache) - only the human-readable
    `summary` string is what gets cached.

    The vehicle read itself is deliberately NOT sudo()'d — see the
    engineering-audit fix note on _tool_get_expiring_documents below,
    the same reasoning applies here. Only the entity-summary cache
    (pure internal bookkeeping, not business data beyond what the
    caller can already read on the vehicle) stays sudo()'d, since it's
    locked to base.group_system the same way the AI response cache is."""
    vehicle_id = arguments.get("vehicle_id")
    if not vehicle_id:
        return {"error": "vehicle_id is required."}
    vehicle = env["deployfleet.vehicle"].browse(int(vehicle_id))
    if not vehicle.exists():
        return {"error": f"No vehicle found with id {vehicle_id}."}

    signature = _vehicle_summary_signature(vehicle)
    cache_model = env["deployfleet.ai.entity.summary"].sudo()
    cached = cache_model.get_cached("deployfleet.vehicle", vehicle.id)
    if cached and cached.source_signature == signature:
        summary_text = cached.summary_text
    else:
        summary_text = _vehicle_summary_text(vehicle)
        cache_model.upsert("deployfleet.vehicle", vehicle.id, summary_text, signature)

    return {
        "id": vehicle.id,
        "license_plate": vehicle.license_plate,
        "status": vehicle.status,
        "vehicle_type": vehicle.vehicle_type_id.name or None,
        "current_driver": vehicle.current_driver_id.name or None,
        "odometer": vehicle.odometer,
        "summary": summary_text,
    }


def _tool_get_due_maintenance(env, _arguments, _feature_key):
    # Not sudo()'d — see the engineering-audit fix note on
    # _tool_get_expiring_documents below.
    schedules = env["deployfleet.maintenance.schedule"].search(
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


def _tool_get_available_drivers(env, arguments, _feature_key):
    """Driver availability is derived, not stored (confirmed by reading
    deployfleet_dispatch_compliance's own _driver_on_approved_leave() —
    there is no single boolean "driver status" field anywhere in the
    domain). Mirrors that same query shape rather than inventing a new
    availability definition."""
    # Not sudo()'d — see the engineering-audit fix note on
    # _tool_get_expiring_documents below. A driver-scoped caller will
    # only see their own leave record via deployfleet.leave.request's
    # own ir.rule, which understates who else is on leave rather than
    # over-exposing it — the correct direction for a degrade.
    target_date = arguments.get("date")
    drivers = env["hr.employee"].search([
        ("deployfleet_is_driver", "=", True),
        ("deployfleet_license_is_expired", "=", False),
    ])
    if target_date:
        on_leave_employee_ids = env["deployfleet.leave.request"].search([
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


def _tool_get_unassigned_shipments(env, _arguments, _feature_key):
    # Not sudo()'d — engineering-audit fix: every read tool in this file
    # previously bypassed its target model's own ACL via sudo() with no
    # company or role filter of its own, letting a low-trust caller (a
    # driver has no direct ACL row on several of these models) extract
    # company-wide operational data through chat that the model's own
    # access rules would otherwise deny. Running as the calling user
    # lets the model's real ACL/record rules govern the result, exactly
    # as if that user browsed the underlying list themselves; a denied
    # read surfaces as a normal tool-call failure fed back to the model
    # (execute()'s broad except below), not a crash.
    shipments = env["deployfleet.shipment"].search(
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


def _tool_get_expiring_documents(env, _arguments, _feature_key):
    # Not sudo()'d — see the engineering-audit fix note on
    # _tool_get_unassigned_shipments above. This is the tool the audit
    # specifically flagged: deployfleet.compliance.document has no ACL
    # row for the driver group at all, so a driver previously extracted
    # the full fleet-wide expiring/expired document list — other
    # drivers' license status, other vehicles' insurance state — purely
    # by asking a question that triggered this tool, entirely bypassing
    # a model they have zero direct access to.
    documents = env["deployfleet.compliance.document"].search(
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


def _tool_mark_vehicle_available(env, arguments, feature_key):
    """The first write tool (doc 21 §3/§4/§10 Phase 3): proposes marking
    a vehicle available via the exact same suggestion -> permission
    check -> human approval -> execute -> audit pipeline every other
    AI-initiated write goes through (deployfleet.ai.action.request.
    propose()) - this tool never writes deployfleet.vehicle directly.
    Whether the proposal auto-executes or lands in the approval queue is
    entirely propose()'s own decision (doc 21 §4's allow-list), not
    something this handler special-cases. Deliberately no sudo(): the
    calling user's own ACLs govern the write, exactly as if they clicked
    the Fleet Command Center's own "Mark Available" button themselves."""
    vehicle_id = arguments.get("vehicle_id")
    if not vehicle_id:
        return {"error": "vehicle_id is required."}
    vehicle = env["deployfleet.vehicle"].browse(int(vehicle_id))
    if not vehicle.exists():
        return {"error": f"No vehicle found with id {vehicle_id}."}

    request = env["deployfleet.ai.action.request"].propose(
        feature_key=feature_key,
        action_type="mark_vehicle_available",
        target_model="deployfleet.vehicle",
        target_id=vehicle.id,
        proposed_vals={},
        action_method="action_set_available",
        source_context="copilot_chat",
    )
    if request.state == "executed":
        return {
            "status": "executed",
            "vehicle_id": vehicle.id,
            "message": f"Vehicle {vehicle.license_plate} marked available.",
        }
    if request.state == "failed":
        return {"status": "failed", "error": request.error_message}
    return {
        "status": "pending_approval",
        "request_name": request.name,
        "message": "Submitted for manager approval - not yet executed.",
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
    "mark_vehicle_available": _tool_mark_vehicle_available,
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

    def execute(self, arguments, feature_key=None):
        """Runs this tool's handler via the fixed dispatch table. Never
        raises — an unknown key or a handler exception both become an
        {"error": ...} dict so a bad tool call degrades to something the
        model can react to, rather than aborting the whole chat turn.

        `feature_key` is passed through to the handler so a write tool
        can attribute its deployfleet.ai.action.request.propose() call to
        the same feature the calling agent/session is already using -
        every read-only handler ignores it."""
        self.ensure_one()
        handler = _TOOL_HANDLERS.get(self.key)
        if not handler:
            return {"error": f"Tool '{self.key}' has no registered handler."}
        try:
            return handler(self.env, arguments or {}, feature_key)
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
        registry exists to enforce. Closes over this agent's own
        feature_id.key so a write tool's propose() call (doc 21 §4)
        attributes to the same feature the calling session is already
        using, not a hardcoded one."""
        tools_by_key = {tool.key: tool for tool in self.search([("agent_ids", "=", agent.id)])}
        feature_key = agent.feature_id.key

        def executor(name, arguments):
            tool = tools_by_key.get(name)
            if not tool:
                return {"error": f"Tool '{name}' is not available to this agent."}
            return tool.execute(arguments, feature_key=feature_key)

        return executor
