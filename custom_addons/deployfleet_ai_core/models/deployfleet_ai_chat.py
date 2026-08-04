from odoo import fields, models

# How many recent messages (both roles) to fold into the prompt sent to
# complete() for multi-turn context - a deliberately simple, bounded
# approach for doc 21 §10's Phase 1 (see docs/architecture/
# 21-copilot-rail-architecture.md §10): real conversation memory without
# changing deployfleet.ai.core.complete()'s signature or adding a second
# call path to a provider. Later phases may replace this with the
# tool-calling/structured-output pipeline doc 21 describes.
_MAX_HISTORY_MESSAGES = 20


class DeployfleetAIChatSession(models.Model):
    """Persistent, named, multi-turn conversation with one AI agent -
    the Copilot Rail's Chat tab (doc 21 §5/§9). Previously modeled but
    entirely unused since Phase 0 (confirmed by the AI & Intelligence
    domain audit: zero views, zero menu, zero controller, zero
    reference anywhere in the codebase) - this is that model finally
    getting a real consumer, extended rather than rebuilt.

    `feature_id`/`system_prompt` (not `agent_id`) deliberately keep this
    module self-contained: `deployfleet_ai_core` must never depend on
    `deployfleet_ai_agents` (that would invert this project's own
    module-layering rule - ai_core is the substrate every other AI
    module depends on, never the reverse, the same discipline that kept
    deployfleet_trip from depending on deployfleet_dispatch directly).
    The Copilot Rail resolves "which agent" in the UI (reading
    `deployfleet.ai.agent`, which it can already soft-couple to) and
    passes that agent's `feature_id` plus a snapshot of its
    `system_prompt_template` when creating a session - the session then
    keeps using that snapshot for its whole lifetime, even if the
    agent's own prompt is edited later, which is the more correct
    behavior for a single coherent conversation.
    """

    _name = "deployfleet.ai.chat.session"
    _description = "DeployFleet AI Assistant Chat Session"
    _order = "create_date desc"

    name = fields.Char(default="New Chat", required=True)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user, required=True)
    feature_id = fields.Many2one(
        "deployfleet.ai.feature", required=True,
        help="Which feature this session's messages route through - policy/permission/budget/cache "
             "checks all key off this, the same as every other deployfleet.ai.core caller.",
    )
    system_prompt = fields.Text(
        required=True,
        help="Snapshot of the agent's system prompt at session-creation time - stays fixed for "
             "this session even if the source agent's prompt is edited later.",
    )
    favorite = fields.Boolean(default=False)
    archived = fields.Boolean(default=False)
    message_ids = fields.One2many("deployfleet.ai.chat.message", "session_id")

    def action_send_message(self, content):
        """Persists the user's message, calls the router with a bounded
        recent-history transcript for multi-turn context, persists the
        assistant's reply, and returns the reply text. The one entry
        point the Copilot Rail's Chat tab calls - it never talks to
        deployfleet.ai.core directly, so every session always has a
        complete, ordered record of what was actually asked and
        answered."""
        self.ensure_one()
        message_model = self.env["deployfleet.ai.chat.message"]
        message_model.create({"session_id": self.id, "role": "user", "content": content})

        recent = self.message_ids.sorted("create_date")[-_MAX_HISTORY_MESSAGES:]
        transcript = "\n".join(
            f"{'User' if message.role == 'user' else 'Assistant'}: {message.content}" for message in recent
        )
        reply = self.env["deployfleet.ai.core"].complete(self.feature_id.key, self.system_prompt, transcript)

        message_model.create({"session_id": self.id, "role": "assistant", "content": reply})
        return reply


class DeployfleetAIChatMessage(models.Model):
    _name = "deployfleet.ai.chat.message"
    _description = "DeployFleet AI Assistant Chat Message"
    _order = "create_date asc"

    session_id = fields.Many2one("deployfleet.ai.chat.session", required=True, ondelete="cascade")
    role = fields.Selection([("user", "User"), ("assistant", "Assistant")], required=True)
    content = fields.Text(required=True)
