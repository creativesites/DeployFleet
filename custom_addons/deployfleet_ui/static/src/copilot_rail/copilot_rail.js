/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { DeployfleetButton } from "../components/button/button";
import { copilotContextStore } from "./copilot_context";
import { DeployfleetChatMessageRenderer } from "./chat_message_renderer";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

/**
 * The Copilot Rail (doc 16 §6/§8, Phase C / Slice 4) — a persistent,
 * collapsed-by-default docked panel present across every workspace,
 * violet-accented per doc 17's AI-content convention, never auto-executing
 * anything per the mandatory suggestion -> approval -> execute pipeline
 * ([08-ai-architecture.md](../../../../../docs/architecture/08-ai-architecture.md) §5,
 * CLAUDE.md §4, hard risk #7).
 *
 * **Two tabs: Approvals (unchanged) and Chat (new — doc 21 §5/§9/§10
 * Phase 1, extended in Phase 1b).** The Chat tab is a persistent,
 * multi-session, real-history-grounded conversation with one of the six
 * `deployfleet.ai.agent` personas, built on `deployfleet.ai.chat.session`/
 * `.message` — modeled since Phase 0 but completely unused until now (see
 * the AI & Intelligence domain audit in CLAUDE.md). Every message still
 * routes through `deployfleet.ai.chat.session.action_send_message()`,
 * which persists both turns and builds a bounded recent-history
 * transcript for multi-turn context — so policy/permission/budget/cache
 * checks all still apply identically. Server-side (deployfleet_ai_agents'
 * `_get_reply()` override — see docs/architecture/
 * 21-copilot-rail-architecture.md §3/§10), a session whose agent has
 * registered tools now routes through `complete_with_tools()` instead of
 * plain `complete()`, so the assistant can look up live vehicle/
 * maintenance/dispatch/compliance data before answering — invisible to
 * this component, which still just calls `action_send_message()`.
 * **Still deliberately not built**: rich in-chat components, auto-execute
 * actions, the memory/entity-summary layer — doc 21 §10's Phases 2–4.
 *
 * `useCopilotContext()` (doc 21 §2, `./copilot_context.js`) lets a
 * workspace publish "what the user is looking at" into a small shared
 * store; this component reads it via `useState(copilotContextStore)` to
 * show a context chip and fold a `context_note` into the next message
 * sent — never persisted on the message itself, only used to steer that
 * turn's answer (see `action_send_message()`'s own docstring).
 *
 * A new session picks an agent up front (from `deployfleet.ai.agent`) —
 * the session then keeps using that agent's feature/prompt for its whole
 * lifetime, the same per-agent framing the Copilot Console's own "Ask"
 * box already established, rather than inventing a new generic assistant
 * identity.
 *
 * `Alt+A` (unchanged) opens the Rail to whichever tab was last active.
 *
 * Soft-coupling: deployfleet.ai.action.request/deployfleet.ai.chat.session/
 * deployfleet.ai.chat.message/deployfleet.ai.agent are referenced as plain
 * runtime strings, the same decision made throughout deployfleet_ui.
 */
export class DeployfleetCopilotRail extends Component {
    static template = "deployfleet_ui.CopilotRail";
    static components = { DeployfleetButton, DeployfleetChatMessageRenderer, DeployfleetErrorBanner };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        // useState() on the module-level copilotContextStore (rather than
        // reading it directly) registers this component as a subscriber,
        // so the Rail re-renders whenever a workspace publishes/clears
        // context via useCopilotContext() - the standard Owl pattern for
        // a store shared across independently-mounted components.
        this.copilotContext = useState(copilotContextStore);
        this.state = useState({
            open: false,
            activeTab: "approvals",
            loading: true,
            pendingApprovals: [],
            actingRequestId: null,
            rejectDialog: null,
            // Chat
            chatLoaded: false,
            chatView: "sessions",
            sessions: [],
            showArchived: false,
            agents: [],
            newSessionAgentId: "",
            creatingSession: false,
            selectedSessionId: null,
            messagesBySessionId: {},
            newMessageText: "",
            sendingMessage: false,
            renamingSessionId: null,
            renameText: "",
        });

        useHotkey("alt+a", () => this.toggleOpen(), { global: true, allowRepeat: false });
        useHotkey(
            "escape",
            () => {
                if (this.state.open) {
                    this.close();
                }
            },
            { global: true, allowRepeat: false },
        );

        onWillStart(() => this.loadPendingApprovals());
    }

    async loadPendingApprovals() {
        this.state.loading = true;
        this.state.loadError = null;
        try {
            // action_method/target_id are included per the engineering-audit
            // fix: an action_method request's proposed_vals is typically {}
            // (the real effect is the method call, not a field write), so
            // omitting action_method here left the approver unable to see
            // what they were actually approving. auto_executed is included
            // too, so the queue is honest about which requests already ran.
            this.state.pendingApprovals = await this.orm.searchRead(
                "deployfleet.ai.action.request",
                [["state", "=", "pending_approval"]],
                [
                    "name", "feature_id", "action_type", "target_model", "target_id",
                    "proposed_vals", "action_method", "auto_executed", "requested_by",
                ],
                { order: "create_date asc" },
            );
        } catch (error) {
            this.state.loadError = extractErrorMessage(error);
        } finally {
            this.state.loading = false;
        }
    }

    get pendingCount() {
        return this.state.pendingApprovals.length;
    }

    /** Plain-text description of what the user is currently looking at
     * elsewhere in the app (doc 21 §2), or null if no workspace has
     * published context. Shown as a chip above the composer and folded
     * into the prompt for the next message sent. */
    get contextNote() {
        if (!this.copilotContext.recordId) {
            return null;
        }
        const domainPrefix = this.copilotContext.domain ? `${this.copilotContext.domain}: ` : "";
        return `Viewing ${domainPrefix}${this.copilotContext.recordLabel} `
            + `(${this.copilotContext.model} #${this.copilotContext.recordId})`;
    }

    /** doc 21 §5's transparency detail: which tool(s) an assistant turn
     * actually invoked, as a short "looked up: ..." line. */
    formattedToolCalls(toolCalls) {
        if (!toolCalls || !toolCalls.length) {
            return "";
        }
        return toolCalls.map((call) => call.tool).join(", ");
    }

    formattedProposedVals(proposedVals) {
        try {
            return JSON.stringify(JSON.parse(proposedVals), null, 2);
        } catch {
            return proposedVals;
        }
    }

    toggleOpen() {
        if (this.state.open) {
            this.close();
        } else {
            this.state.open = true;
            this.loadPendingApprovals();
        }
    }

    close() {
        this.state.open = false;
        this.state.rejectDialog = null;
    }

    async onSelectTab(tabKey) {
        this.state.activeTab = tabKey;
        if (tabKey === "chat" && !this.state.chatLoaded) {
            this.state.chatLoaded = true;
            await Promise.all([this.loadSessions(), this.loadAgents()]);
        }
    }

    async onApprove(requestId) {
        this.state.actingRequestId = requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_approve", [[requestId]]);
            await this.loadPendingApprovals();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }

    onOpenRejectDialog(requestId) {
        this.state.rejectDialog = { requestId, reasonText: "" };
    }

    onRejectReasonInput(ev) {
        if (this.state.rejectDialog) {
            this.state.rejectDialog.reasonText = ev.target.value;
        }
    }

    onCancelReject() {
        this.state.rejectDialog = null;
    }

    async onConfirmReject() {
        const dialog = this.state.rejectDialog;
        if (!dialog) {
            return;
        }
        this.state.actingRequestId = dialog.requestId;
        try {
            await this.orm.call("deployfleet.ai.action.request", "action_reject", [
                [dialog.requestId],
                dialog.reasonText,
            ]);
            this.state.rejectDialog = null;
            await this.loadPendingApprovals();
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.actingRequestId = null;
        }
    }

    // ---------------------------------------------------------------
    // Chat (doc 21 §5/§9, Phase 1)
    // ---------------------------------------------------------------

    async loadSessions() {
        this.state.sessions = await this.orm.searchRead(
            "deployfleet.ai.chat.session",
            [],
            ["name", "feature_id", "favorite", "archived"],
            { order: "create_date desc" },
        );
    }

    async loadAgents() {
        this.state.agents = await this.orm.searchRead(
            "deployfleet.ai.agent",
            [],
            ["name", "feature_id", "system_prompt_template"],
            { order: "sequence asc" },
        );
    }

    get filteredSessions() {
        return this.state.sessions.filter((s) => Boolean(s.archived) === this.state.showArchived);
    }

    onNewSessionAgentInput(value) {
        this.state.newSessionAgentId = value;
    }

    async onCreateSession() {
        const agent = this.state.agents.find((a) => a.id === parseInt(this.state.newSessionAgentId, 10));
        if (!agent) {
            this.notification.add("Choose an agent to start a chat with.", { type: "danger" });
            return;
        }
        this.state.creatingSession = true;
        try {
            const [sessionId] = await this.orm.create("deployfleet.ai.chat.session", [
                {
                    name: `Chat with ${agent.name}`,
                    feature_id: agent.feature_id[0],
                    system_prompt: agent.system_prompt_template,
                },
            ]);
            await this.loadSessions();
            this.state.newSessionAgentId = "";
            await this.onSelectSession(sessionId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        } finally {
            this.state.creatingSession = false;
        }
    }

    async onSelectSession(sessionId) {
        this.state.selectedSessionId = sessionId;
        this.state.chatView = "conversation";
        if (!this.state.messagesBySessionId[sessionId]) {
            await this.loadMessages(sessionId);
        }
    }

    async loadMessages(sessionId) {
        const messages = await this.orm.searchRead(
            "deployfleet.ai.chat.message",
            [["session_id", "=", sessionId]],
            ["role", "content", "tool_calls", "rich_payload"],
            { order: "create_date asc" },
        );
        this.state.messagesBySessionId[sessionId] = messages.map((message) => ({
            ...message,
            toolCalls: this.parseJsonField(message.tool_calls),
            richPayload: this.parseJsonField(message.rich_payload),
        }));
    }

    /** `tool_calls`/`rich_payload` come back from the ORM as either a JSON
     * string or `false` (Odoo's empty-Text convention) - never trust the
     * exact shape, degrade to null on anything unparseable rather than
     * breaking the conversation view. */
    parseJsonField(value) {
        if (!value) {
            return null;
        }
        try {
            return JSON.parse(value);
        } catch {
            return null;
        }
    }

    onBackToSessions() {
        this.state.chatView = "sessions";
    }

    async onToggleFavorite(session) {
        try {
            await this.orm.write("deployfleet.ai.chat.session", [session.id], { favorite: !session.favorite });
            session.favorite = !session.favorite;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        }
    }

    async onToggleArchive(session) {
        try {
            await this.orm.write("deployfleet.ai.chat.session", [session.id], { archived: !session.archived });
            session.archived = !session.archived;
            if (this.state.selectedSessionId === session.id) {
                this.state.chatView = "sessions";
            }
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        }
    }

    onStartRename(session) {
        this.state.renamingSessionId = session.id;
        this.state.renameText = session.name;
    }

    onRenameInput(ev) {
        this.state.renameText = ev.target.value;
    }

    async onSaveRename(session) {
        const name = this.state.renameText.trim();
        if (!name) {
            return;
        }
        try {
            await this.orm.write("deployfleet.ai.chat.session", [session.id], { name });
            session.name = name;
            this.state.renamingSessionId = null;
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
        }
    }

    onNewMessageInput(ev) {
        this.state.newMessageText = ev.target.value;
    }

    async onSendMessage() {
        const text = this.state.newMessageText.trim();
        const sessionId = this.state.selectedSessionId;
        if (!text || !sessionId) {
            return;
        }
        this.state.sendingMessage = true;
        this.state.newMessageText = "";
        this.state.messagesBySessionId[sessionId].push({ role: "user", content: text });
        try {
            await this.orm.call("deployfleet.ai.chat.session", "action_send_message", [
                [sessionId],
                text,
                this.contextNote,
            ]);
            // Reload rather than push a plain-text bubble: the persisted
            // assistant message may carry tool_calls/rich_payload (doc 21
            // §5/§7) this component has no way to reconstruct from the
            // bare reply string action_send_message() returns.
            await this.loadMessages(sessionId);
        } catch (error) {
            this.notification.add(extractErrorMessage(error), { type: "danger" });
            // Reload from the server so the optimistic user-message append
            // above doesn't drift from what actually persisted (the write
            // happens before complete() can fail, so the user turn is
            // real even if the assistant turn errored out).
            await this.loadMessages(sessionId);
        } finally {
            this.state.sendingMessage = false;
        }
    }
}

registry.category("main_components").add("deployfleet_ui.CopilotRail", {
    Component: DeployfleetCopilotRail,
});
