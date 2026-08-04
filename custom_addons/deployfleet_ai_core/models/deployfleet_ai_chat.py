import json
import logging
import re

from odoo import fields, models

_logger = logging.getLogger(__name__)

# How many recent messages (both roles) to fold into the prompt sent to
# complete() for multi-turn context - a deliberately simple, bounded
# approach for doc 21 §10's Phase 1 (see docs/architecture/
# 21-copilot-rail-architecture.md §10): real conversation memory without
# changing deployfleet.ai.core.complete()'s signature or adding a second
# call path to a provider. Later phases may replace this with the
# tool-calling/structured-output pipeline doc 21 describes.
_MAX_HISTORY_MESSAGES = 20

# doc 21 §7's structured-output contract, reached via a portable trailing
# ```json {...} ``` fenced block rather than each provider's own native
# JSON-mode/structured-output parameter (a deliberate deviation - native
# JSON-mode needs a provider-specific request shape per adapter, and this
# convention works identically across all three providers with zero
# adapter changes, at the cost of relying on the model actually following
# the instruction rather than a hard API guarantee).
_RICH_PAYLOAD_FENCE_RE = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)


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

    def action_send_message(self, content, context_note=None):
        """Persists the user's message, calls the router with a bounded
        recent-history transcript for multi-turn context, persists the
        assistant's reply, and returns the reply text. The one entry
        point the Copilot Rail's Chat tab calls - it never talks to
        deployfleet.ai.core directly, so every session always has a
        complete, ordered record of what was actually asked and
        answered.

        `context_note` (doc 21 §2/§10 Phase 1b) is an optional plain-text
        description of what the user is currently looking at elsewhere in
        the app (e.g. "viewing shipment SHP-0042"), supplied by the
        frontend's useCopilotContext() store. It is folded into the
        transcript sent to the model for this turn only - deliberately
        never persisted on the message record itself, so the visible chat
        history stays exactly what the user typed and heard back.

        The assistant's raw reply may end with a ```json {...} ``` block
        (doc 21 §7's structured-output contract) - extracted here into
        `rich_payload` before the plain-text remainder is persisted as
        `content`, so the transcript folded into future turns and the
        chat bubble the user sees both stay clean prose, never raw JSON."""
        self.ensure_one()
        message_model = self.env["deployfleet.ai.chat.message"]
        message_model.create({"session_id": self.id, "role": "user", "content": content})

        recent = self.message_ids.sorted("create_date")[-_MAX_HISTORY_MESSAGES:]
        transcript = "\n".join(
            f"{'User' if message.role == 'user' else 'Assistant'}: {message.content}" for message in recent
        )
        if context_note:
            transcript = f"[Context: {context_note}]\n{transcript}"
        reply = self._get_reply(transcript)

        rich_payload, plain_text = self._extract_rich_payload(reply["text"])
        message_model.create({
            "session_id": self.id, "role": "assistant", "content": plain_text,
            "tool_calls": json.dumps(reply["tool_calls"]) if reply["tool_calls"] else False,
            "rich_payload": json.dumps(rich_payload) if rich_payload else False,
        })
        return plain_text

    def _get_reply(self, transcript):
        """Produces the assistant's reply for a turn, as
        `{"text": str, "tool_calls": [{"tool": ..., "args": ...}, ...]}`.
        Plain deployfleet.ai.core.complete() (empty tool_calls) by default
        - deployfleet_ai_agents overrides this via _inherit to route
        through complete_with_tools() instead and populate tool_calls,
        the same overridable-hook pattern this codebase already uses for
        _score_candidate() (deployfleet_dispatch_compliance extending
        deployfleet_dispatch). Kept as a separate method (rather than
        inlined in action_send_message()) specifically so that override
        point exists without deployfleet_ai_core ever needing to depend
        on deployfleet_ai_agents."""
        self.ensure_one()
        text = self.env["deployfleet.ai.core"].complete(
            self.feature_id.key, self._effective_system_prompt(), transcript,
        )
        return {"text": text, "tool_calls": []}

    def _effective_system_prompt(self):
        """The session's own system_prompt snapshot, with the company's
        AI profile (doc 21 §6 - deployfleet.ai.company.profile) prepended
        when one exists. Deliberately computed fresh on every call rather
        than folded into the stored system_prompt snapshot - the company
        profile can be edited after the session started, and the next
        turn should see the current text, the same reasoning that already
        keeps context_note out of the persisted transcript."""
        self.ensure_one()
        profile = self.env["deployfleet.ai.company.profile"].sudo().search(
            [("company_id", "=", self.env.company.id)], limit=1,
        )
        if profile and profile.profile_text:
            return f"Company context: {profile.profile_text}\n\n{self.system_prompt}"
        return self.system_prompt

    def _extract_rich_payload(self, text):
        """Pulls an optional trailing ```json {...} ``` block out of a
        plain-text reply (doc 21 §7). Returns (rich_payload_dict_or_None,
        plain_text_with_the_block_removed). Never raises - an absent or
        malformed block just means no rich payload, the same "never trust
        the exact shape" defensiveness the provider adapters already
        apply to token-usage parsing."""
        match = _RICH_PAYLOAD_FENCE_RE.search(text)
        if not match:
            return None, text
        try:
            payload = json.loads(match.group(1))
        except ValueError:
            _logger.warning("deployfleet.ai.chat.session: malformed rich-payload JSON block, ignoring it")
            return None, text
        if not isinstance(payload, dict) or "components" not in payload:
            return None, text
        plain_text = (text[:match.start()] + text[match.end():]).strip()
        return payload, plain_text or text


class DeployfleetAIChatMessage(models.Model):
    _name = "deployfleet.ai.chat.message"
    _description = "DeployFleet AI Assistant Chat Message"
    _order = "create_date asc"

    session_id = fields.Many2one("deployfleet.ai.chat.session", required=True, ondelete="cascade")
    role = fields.Selection([("user", "User"), ("assistant", "Assistant")], required=True)
    content = fields.Text(required=True)
    tool_calls = fields.Text(
        help="JSON list of {'tool', 'args'} this turn invoked (doc 21 §5) - populated only for "
             "assistant messages from a tooled agent session; empty/false otherwise.",
    )
    rich_payload = fields.Text(
        help="JSON {'components': [...], 'actions_available': [...]} extracted from the assistant's "
             "reply (doc 21 §7) - lets the frontend's ChatMessageRenderer (doc 21 §8) render rich "
             "components instead of only `content`'s plain text; empty/false when absent.",
    )
