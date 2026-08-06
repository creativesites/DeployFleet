/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { DeployfleetButton } from "../components/button/button";
import { DeployfleetAvatar } from "../components/avatar/avatar";
import { copilotContextStore } from "./copilot_context";
import { DeployfleetChatMessageRenderer } from "./chat_message_renderer";

import { DeployfleetErrorBanner } from "../components/error_banner/error_banner";

function extractErrorMessage(error) {
    return error?.data?.message || error?.message || "Something went wrong. Please try again.";
}

// Friendly label/icon for each deployfleet.ai.tool key (doc 21 §3's
// registry) shown as a chip under an assistant message that invoked it -
// a static client-side map, not a live read of deployfleet.ai.tool,
// deliberately: group_deployfleet_driver has no ACL grant on that model
// (dispatcher+ only, security/ir.model.access.csv in deployfleet_ai_agents),
// and a driver-only demo/real session must still be able to see which
// tool an assistant turn used. Six known keys as of doc 21 §10 Phase
// 1b/3 - an unrecognized key (a future tool this map hasn't been updated
// for) falls back to its raw key with a generic search icon rather than
// being hidden.
const TOOL_LABEL = {
    get_vehicle_summary: { label: "Vehicle status", icon: "fa fa-truck" },
    get_due_maintenance: { label: "Due maintenance", icon: "fa fa-wrench" },
    get_available_drivers: { label: "Available drivers", icon: "fa fa-id-card" },
    get_unassigned_shipments: { label: "Unassigned shipments", icon: "fa fa-cube" },
    get_expiring_documents: { label: "Expiring documents", icon: "fa fa-file-text-o" },
    mark_vehicle_available: { label: "Mark vehicle available", icon: "fa fa-check-circle" },
};

// First-run per-agent onboarding (doc 21's Phase C/D UX follow-up):
// suggested prompts shown on a brand-new, message-free session, keyed by
// deployfleet.ai.agent.key. fleet_analyst/dispatch_agent/maintenance_agent/
// compliance_agent have real registered tools (deployfleet_ai_tool_data.xml)
// so their prompts intentionally imply a live lookup; finance_agent/
// customer_agent have none yet (that data file's own comment: "deliberately
// excluded for now") so their prompts stay general-reasoning questions
// rather than implying live data this session can't actually fetch.
const AGENT_WELCOME = {
    fleet_analyst: {
        icon: "fa fa-truck",
        prompts: [
            "Which vehicles are currently in breakdown or maintenance?",
            "Summarize the status of a specific vehicle by its license plate.",
        ],
    },
    dispatch_agent: {
        icon: "fa fa-th-large",
        prompts: [
            "Which drivers are available today?",
            "What shipments still need a vehicle assigned?",
        ],
    },
    maintenance_agent: {
        icon: "fa fa-wrench",
        prompts: [
            "What maintenance is due soon across the fleet?",
            "Summarize a vehicle's current maintenance status.",
        ],
    },
    compliance_agent: {
        icon: "fa fa-shield",
        prompts: [
            "What compliance documents are expiring soon?",
            "Which vehicles or drivers have expired documents right now?",
        ],
    },
    finance_agent: {
        icon: "fa fa-money",
        prompts: [
            "What should I look at first to control costs this month?",
            "Explain how the gross margin approximation on Financial Intelligence is calculated.",
        ],
    },
    customer_agent: {
        icon: "fa fa-users",
        prompts: [
            "What should I gather before onboarding a new customer?",
            "How does a rate card differ from a contract?",
        ],
    },
};
const DEFAULT_AGENT_WELCOME = { icon: "fa fa-magic", prompts: [] };

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
    static components = { DeployfleetButton, DeployfleetAvatar, DeployfleetChatMessageRenderer, DeployfleetErrorBanner };
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
            ["key", "name", "description", "feature_id", "system_prompt_template"],
            { order: "sequence asc" },
        );
    }

    get filteredSessions() {
        return this.state.sessions.filter((s) => Boolean(s.archived) === this.state.showArchived);
    }

    /** The deployfleet.ai.agent behind the currently-open session, found
     * by matching feature_id back to the loaded agent catalog — sessions
     * deliberately don't store agent_id (see this file's own module
     * docstring: deployfleet_ai_core must never depend on
     * deployfleet_ai_agents), so this is the only way to recover "which
     * agent is this" for the welcome state/suggested prompts below. */
    get selectedAgent() {
        const session = this.state.sessions.find((s) => s.id === this.state.selectedSessionId);
        if (!session) {
            return null;
        }
        return this.state.agents.find((a) => a.feature_id[0] === session.feature_id[0]) || null;
    }

    get selectedAgentWelcome() {
        const agent = this.selectedAgent;
        return (agent && AGENT_WELCOME[agent.key]) || DEFAULT_AGENT_WELCOME;
    }

    /** Current user's avatar, standard Odoo image-controller URL — the
     * same convention used throughout the web client for a user's own
     * avatar (no new RPC: user.userId already comes from the existing
     * @web/core/user session singleton). */
    get currentUserAvatarUrl() {
        return `/web/image/res.users/${user.userId}/avatar_128`;
    }

    /** doc 21 §5's transparency detail, rendered as chips rather than a
     * plain comma-joined string: {key, label, icon} per tool call, using
     * TOOL_LABEL when known and falling back to the raw key otherwise so
     * a future tool this map hasn't caught up with still shows *something*
     * rather than being silently dropped. */
    toolCallChips(toolCalls) {
        return (toolCalls || []).map((call) => ({
            key: call.tool,
            ...(TOOL_LABEL[call.tool] || { label: call.tool, icon: "fa fa-search" }),
        }));
    }

    onUseSuggestedPrompt(prompt) {
        this.state.newMessageText = prompt;
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
            ["role", "content", "tool_calls", "rich_payload", "create_date"],
            { order: "create_date asc" },
        );
        this.state.messagesBySessionId[sessionId] = messages.map((message) => ({
            ...message,
            toolCalls: this.parseJsonField(message.tool_calls),
            richPayload: this.parseJsonField(message.rich_payload),
        }));
    }

    /** Odoo returns datetime fields as naive UTC strings ("YYYY-MM-DD
     * HH:MM:SS", no timezone marker) — parsing that directly with
     * `new Date(str)` is interpreted as *local* time by JS, silently
     * shifting every timestamp by the browser's UTC offset (the exact
     * class of bug the engineering audit's C-16 fix already closed on
     * the Trip Board calendar; reusing that same fix's
     * `replace(" ", "T") + "Z"` pattern here rather than reintroducing
     * it). */
    formattedMessageTime(createDate) {
        if (!createDate) {
            return "";
        }
        const date = new Date(createDate.replace(" ", "T") + "Z");
        return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
    }

    /** Approvals tab: a flat, single-level object renders as a readable
     * key/value list instead of raw JSON; anything nested or unparseable
     * falls back to the existing <pre> JSON view (formattedProposedVals)
     * rather than trying to flatten arbitrary structures. */
    proposedValsEntries(proposedVals) {
        let parsed;
        try {
            parsed = JSON.parse(proposedVals);
        } catch {
            return null;
        }
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return null;
        }
        const entries = Object.entries(parsed);
        if (!entries.length || entries.some(([, value]) => value !== null && typeof value === "object")) {
            return null;
        }
        return entries;
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
