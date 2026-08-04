from odoo import models


class DeployfleetAIChatSession(models.Model):
    """Adds tool-calling on top of deployfleet_ai_core's plain-text
    _get_reply() — docs/architecture/21-copilot-rail-architecture.md
    §3/§10 Phase 1b. deployfleet_ai_core has no knowledge of
    deployfleet.ai.agent/deployfleet.ai.tool at all and never will (ai_core
    is the substrate every AI module depends on, never the reverse); this
    _inherit, living in deployfleet_ai_agents, is the only place that
    dependency exists — the same overridable-hook pattern this codebase
    already uses for deployfleet_dispatch_compliance extending
    deployfleet_dispatch's _score_candidate()."""

    _inherit = "deployfleet.ai.chat.session"

    def _get_reply(self, transcript):
        self.ensure_one()
        agent = self.env["deployfleet.ai.agent"].search([("feature_id", "=", self.feature_id.id)], limit=1)
        if not agent:
            return super()._get_reply(transcript)

        tool_model = self.env["deployfleet.ai.tool"]
        tools = tool_model.schemas_for_agent(agent)
        if not tools:
            return super()._get_reply(transcript)

        executor = tool_model.build_executor(agent)
        tool_call_log = []
        text = self.env["deployfleet.ai.core"].complete_with_tools(
            self.feature_id.key, self._effective_system_prompt(), transcript, tools,
            executor=executor, tool_call_log=tool_call_log,
        )
        return {"text": text, "tool_calls": tool_call_log}
