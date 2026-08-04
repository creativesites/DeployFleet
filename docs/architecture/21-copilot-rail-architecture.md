# 21 — Copilot Rail: Agentic Assistant Architecture

**Status:** Design doc, written before any implementation, per explicit user direction ("write an architecture doc first") after a product vision brief for the Copilot Rail was delivered mid-session. Same discipline as [08-ai-architecture.md](08-ai-architecture.md) and [16-experience-architecture.md](16-experience-architecture.md) — no code for this initiative should be written until this document's approach is agreed, the same way no Experience Architecture screen was built before doc 16 existed.

**§10 Phase 1 is built** — plain-text, session-persisted, multi-turn Chat in the Copilot Rail. **§10 Phase 1b is now also built** — §3's provider-native tool-calling (`deployfleet.ai.core.complete_with_tools()`, the `deployfleet.ai.tool` fixed-dispatch registry in `deployfleet_ai_agents`, 5 read-only tools) and §2's `useCopilotContext()` hook (wired into Fleet Command Center and the Dispatch Board, folded into the Chat prompt as a non-persisted `context_note`). See CLAUDE.md's AI & Intelligence writeup for the concrete implementation notes and the deliberate deviations from this doc's original sketch (fixed dict-dispatch tool execution instead of dynamic `getattr`, live-provider verification still outstanding per §11 item 3). §4's execution tiering, §6's memory layer, §7's structured outputs, and §8's rich components remain **designed, not built** — Phases 2–4 are still future work, not started.

**What this supersedes:** the *ambient* half of the Copilot Rail (Phase C Slice 4 — a collapsed badge + pending-approval queue) and the *destination* half (the Copilot Console — Phase D Slice 1, agent catalog + usage dashboard + a stateless single-question "Ask" box) are both already built and shipped. This document does not redesign either — it adds a third, much larger capability neither one has: a persistent, context-aware, tool-calling, multi-turn **Chat** experience with real action execution. Read [18-component-library.md](18-component-library.md)'s Copilot Rail entry and this repo's `deployfleet_ui/static/src/copilot_rail/` and `copilot_console/` source before touching either — this build extends them, it does not replace them.

---

## 0. What already exists — reuse audit, not assumed

The single biggest finding of this doc's own research: **the chat data model this vision needs was already built and has sat completely unused since Phase 0.**

| Piece this vision needs | Already exists? | Where |
|---|---|---|
| Multi-session, persisted chat storage | **Yes, fully modeled, zero consumers** | `deployfleet.ai.chat.session` (`name`, `user_id`, `message_ids`) / `deployfleet.ai.chat.message` (`session_id`, `role`, `content`) in `deployfleet_ai_core`. Full `base.group_user` CRUD ACL already granted (the *only* AI-core model with that shape of grant — see the AI & Intelligence domain audit this session). Zero views, zero menu, zero controller, zero reference anywhere in the ~50-module codebase. This is exactly the "conversation with history, rename, continue" requirement from the vision brief — it needs a `favorite`/`archived` boolean added and a real UI, not a new model. |
| Provider-agnostic call routing, caching, cost/usage logging | **Yes, production-hardened this session** | `deployfleet.ai.core.complete()` (§2 of doc 08) — just fixed this session (the headline ACL bug: `sudo()` added to its internal config/budget/cache reads so real roles can actually call it). Every new capability below calls through this same router; nothing in this doc adds a second way to reach a provider. |
| Mandatory suggestion→approval→execute→audit pipeline | **Yes, working, one real producer today** | `deployfleet.ai.action.request` in `deployfleet_ai_actions` (§5 of doc 08) — `draft → pending_approval → approved/rejected → executed/failed`, a forbidden-target-model denylist, `_execute()` writing via the normal ORM as the approver. Today's only real caller is the WhatsApp breakdown handler. §4 below is about *how* Copilot-initiated actions use this pipeline, not about replacing it. |
| Cross-module event bus for cache invalidation | **Yes, already the established pattern** | `deployfleet_event_bus` — any module publishes `register_event(pattern, model, id, payload)`; any module subscribes via a data record naming a handler method, no code change to the publisher. §6 below reuses this verbatim for entity-summary cache invalidation, the same way `deployfleet_trip` already reuses it to spawn trips from confirmed dispatch assignments. |
| Per-feature toggle, per-role permission allow-list, budget/policy gates | **Yes, unchanged** | `deployfleet_ai_permissions`/`deployfleet.ai.policy`/`deployfleet.ai.budget` — every check in `complete()` still runs for every Chat-originated call. Nothing in this doc bypasses them. |

**What's genuinely new**, sized honestly against doc 08's own "70% already built, the action pipeline was the real lift" framing: a **tool-calling contract** (nothing in this codebase lets an LLM decide which of several backend queries to run — §3), an **execution-tiering decision** for chat-initiated writes (§4 — the one place this doc changes an existing hard rule, deliberately and narrowly), a **context/entity-summary/memory layer** (§6 — genuinely does not exist in any form), a **structured-output contract** (§7), and **rich in-chat components** (§8). These four are this initiative's real engineering cost — the same shape of honest sizing doc 08 §0 already modeled for this project.

---

## 1. Product vision, condensed

The user's own framing, kept verbatim as the north star: *"A fleet manager, dispatcher, or company owner should feel like they have an AI operations assistant sitting beside them that already understands their fleet, drivers, customers, finances, compliance, and daily operations."* Concretely: a persistent, collapsible rail present on every workspace; a full multi-session Chat tab with history/rename/archive; context-awareness of the current screen/record; proactive surfacing (not just Q&A); tool-based retrieval so only the data a question actually needs gets fetched; real action execution, not just explanation; rich in-chat components (vehicle cards, tables, charts, approval cards, timelines, inline forms) instead of plain text; a memory/context layer so the assistant doesn't re-derive the same summary every time; and a target feeling of *"I don't need to search through menus. I just ask DeployFleet."*

The bullets below are the engineering decomposition of that vision, each reconciled against what already exists in this codebase (§0) and against CLAUDE.md's non-negotiable AI rules (§4's `git blame` is doc 08 §5 and CLAUDE.md §4 — every capability independently switchable, every call through the router, every write gated, every call logged).

---

## 2. Context awareness — resolved without a native-chrome hook

Doc 16/CLAUDE.md have flagged "per-record contextual awareness" as deferred twice already (Copilot Rail's Phase C build, then again at Phase D Slice 1's Copilot Console) — both times for the same stated reason: doing this by having the Rail introspect Odoo's action-manager internals to discover "what record is the user looking at right now" means depending on an unverified, un-documented internal API of this exact Odoo 19 nightly, the same risk-aversion that already kept the Launcher off a `web.NavBar` patch (doc 16 §3.2).

**This doc resolves it differently, without touching that internal API at all.** Every `deployfleet_ui` workspace component already knows its own domain and (where relevant) its own selected/expanded record — that's just component state, already present in every screen built this session (`state.selectedShipmentId`, `state.selectedVehicleId`, etc.). Context awareness becomes an **explicit, opt-in prop** the host screen passes to the Rail, not something the Rail discovers by inspecting global browser/router state:

```
useCopilotContext({ domain: "fleet", model: "deployfleet.vehicle", recordId: vehicle.id, recordLabel: vehicle.license_plate })
```

A small shared hook (new, `deployfleet_ui/static/src/copilot_rail/copilot_context.js`) that any workspace can call in `setup()`, writing into a shared reactive store the Rail already has access to (both are mounted in the same `main_components` tree). No screen is *required* to call it — the Rail simply has no current-record context if a screen doesn't opt in, and falls back to domain-only or fully generic. This is strictly safer than the deferred approach (no internal API dependency, degrades gracefully, and each screen's own author controls exactly what context is exposed) and costs one hook call per screen to wire in, not a framework-level change — a good first-slice task (§10 Phase 1).

---

## 3. Tool-calling architecture

**The problem the vision brief names correctly:** sending the whole relevant slice of the database as prompt context on every chat turn is both expensive (defeats §3 of doc 08's entire cost-architecture rationale) and unnecessary — most questions need one or two specific facts, not a company-wide dump.

**The mechanism: provider-native function/tool calling**, not a bespoke DeployFleet parser. DeepSeek, OpenAI, and Claude's chat-completion APIs all support passing a list of callable tool schemas (name, description, JSON-schema parameters) and receiving back either a text answer or a structured "call this tool with these arguments" response — this is a standard, well-documented capability of every provider `deployfleet_ai_core` already integrates, not a new provider integration. `_call_provider()` (doc 08 §2) gains an optional `tools` parameter; the adapters (`_call_openai_compatible`, `_call_claude`) pass it through to the provider's existing tool-calling parameter (`tools`/`tool_choice` for OpenAI-compatible, `tools` for Claude's Messages API) and parse a tool-call response back into `(tool_name, tool_args)` instead of plain text.

**Tool registry — the same "data record names a handler, no code change to the caller" pattern as the event bus (§0),** deliberately reused rather than inventing a second registration mechanism in this codebase:

```
deployfleet.ai.tool
├── key                 (unique, e.g. "get_vehicle_summary")
├── name / description  (the LLM-facing schema text)
├── parameters_schema   (JSON Schema, Text field)
├── model_name          (technical model whose method implements this)
├── method_name         (the method — must be explicitly allow-listed, see below)
├── read_only           (Boolean — a read tool executes immediately and always; a write tool is subject to §4's tiering)
└── agent_ids           (M2M deployfleet.ai.agent — which agents may call this tool)
```

A module registers a new tool by adding a data record and implementing the method — never by editing `deployfleet_ai_core`. Mirrors doc 08 §6's own reasoning for why the six agents are data records, not code: a tool is a named, scoped, config-driven capability bundle, not a new plumbing layer per tool.

**Security boundary, non-negotiable regardless of tiering (§4):** a tool's `method_name` must appear on an explicit per-tool allow-list validated at tool-registration time (an `@api.constrains` on `deployfleet.ai.tool`, the same defensive pattern `deployfleet.ai.action.request._check_target_model_not_forbidden()` already uses) — an LLM's tool-call response selects a *tool key*, never an arbitrary model/method pair the way `deployfleet.ai.action.request.target_model`/`target_id` do today. This is a narrower, safer surface than the action-request pipeline's already-forbidden-model denylist (§0): a tool is opt-in allow-list by construction, the action pipeline is opt-out deny-list by construction — both defenses stay in place, layered, not one replacing the other.

**First tool tranche (Phase 1, §10)** — read-only, one or two per existing agent, chosen for being genuinely cheap to implement against models this session already knows well: `get_vehicle_summary(vehicle_id)`, `get_due_maintenance()`, `get_available_drivers()`, `get_unassigned_shipments()`, `get_expiring_documents()`. Every one of these is a thin wrapper around an ORM `search_read` this codebase already performs somewhere in `deployfleet_ui` — the tool layer's job is exposing that same query to the LLM's tool-call mechanism, not inventing new queries.

---

## 4. Action execution tiering — the one deliberate change to an existing hard rule

**The existing rule, restated exactly (doc 08 §5, CLAUDE.md §4, hard risk #7):** *"Any AI-initiated write is gated: suggestion → permission check → human approval → execute → audit log. There is no 'auto-execute' path in v1."* This was, and remains, the single most load-bearing safety principle in this codebase's AI design.

**The user's explicit direction for this initiative:** some chat-initiated actions should execute immediately, without waiting for a separate human-approval step. This is treated here as a deliberate, narrow, structurally-bounded exception — not a reversal of the principle — for three reasons: (1) it only ever applies to Copilot-chat-initiated writes, never to any other AI feature already built; (2) it is opt-in per action type, defaulting closed; (3) the target-model denylist and data-category blocks from the existing pipeline still apply with no exception, at every tier.

**Three tiers, not two:**

| Tier | What it covers | Approval required? | Mechanism |
|---|---|---|---|
| **Read** | Any tool with `read_only=True` (§3) | No — reads never touch the approval pipeline, they're not writes | Executes immediately, result returned in the same turn |
| **Auto-executable write** | A narrow, explicitly curated allow-list of low-blast-radius writes — see criteria below | No human approval step, but **still creates a `deployfleet.ai.action.request` row**, created in state `executed` directly (skipping `pending_approval`) rather than a second, parallel audit mechanism | One audit trail, one place to review "what did the AI actually change," whether it needed approval or not |
| **Approval-required write** | Everything else that writes | Yes, unchanged from today | Existing `draft → pending_approval → approved/rejected → executed/failed` flow, unchanged; Chat surfaces this as an inline approval card (§8) rather than sending the user to the Rail, but the state machine and the manager-only `action_approve()`/`action_reject()` checks are untouched |

**What qualifies for the auto-executable tier — a real criteria list, not "the AI decides":**

1. **Never** a model on `deployfleet.ai.action.request`'s existing `_FORBIDDEN_TARGET_MODELS` denylist (§0) — that list is a shared, single source of truth both pipelines respect.
2. **Never** a feature whose `data_category` is `payroll` or `financial` (`deployfleet.ai.policy`'s existing category blocks, doc 08 §9) — the same category boundary that already keeps AI off payroll/financial data by default stays load-bearing here with zero exception.
3. **Reversible or low-cost-to-reverse only** — e.g., "mark vehicle available", "assign driver to trip" (both already one-click actions on existing screens, not novel capabilities), not "close a workshop job card" (consumes stock, doc 20 §6a) or "confirm an invoice" (accounting-consequential).
4. Marked explicitly via a new `deployfleet.ai.feature.auto_executable` Boolean, **default `False`** — a feature is opt-in to this tier the same way `deployfleet.ai.action.request.target_model` is opt-in to being writable at all; nothing becomes auto-executable by omission.
5. Still subject to every existing gate ahead of it in `complete()` — policy, feature-enabled, AI-permission allow-list, budget. An auto-executable write from a user with no AI permission on that feature still fails exactly as it does today.

**Concrete starting allow-list for Phase 2 (§10)**, deliberately small: `deployfleet.vehicle.action_set_available()`, `deployfleet.dispatch.assignment.action_confirm()` (only when no override is needed — the compliance/higher-score override paths always fall through to the approval tier), `deployfleet.workshop.job.card` status-advance calls that don't consume stock. Every other write starts in the approval-required tier; promoting one to auto-executable is a deliberate, reviewed, one-line ACL-style change per feature — not a blanket switch.

---

## 5. Chat/session model — extend, don't rebuild

`deployfleet.ai.chat.session` gains `favorite` (Boolean) and `archived` (Boolean, default False, so archived sessions leave the default list without being deleted) — nothing else structural changes. `deployfleet.ai.chat.message` gains `tool_calls` (Text, JSON — which tool(s) this turn invoked and their arguments, for a transparent "what did the assistant actually look up" expandable detail) and `rich_payload` (Text, JSON — the structured-output contract from §7, letting the frontend render §8's components instead of only `content`'s plain text). Every message a session ever sends still routes through `deployfleet.ai.core.complete()` (extended with a `tools`/`session_id` signature, §3) — the session/message models are a persistence layer around the existing router, not a parallel path to a provider.

---

## 6. Context/memory layer

Two new models, deliberately small, both cache-shaped (expire and get recomputed, never a source of truth in their own right — the ORM records they summarize always are):

```
deployfleet.ai.entity.summary
├── res_model / res_id      (the entity this summarizes, e.g. deployfleet.vehicle/123)
├── summary_text            (Text — plain-language, LLM-generated)
├── computed_date
├── source_signature        (hash of the inputs used, so a re-fetch can cheaply detect "nothing changed")
```

```
deployfleet.ai.company.profile
├── company_id (unique)
├── profile_text   (Text — fleet size, operating regions, business-rule notes; company-scoped, not per-entity)
├── updated_date
```

**Invalidation via the event bus (§0), not a cron sweep or a TTL guess.** A summary is recomputed only when something it actually depends on changes, using the exact subscription pattern `deployfleet_trip` already uses to spawn trips from dispatch events: a new `deployfleet.event.subscription` row naming `deployfleet.ai.entity.summary` and a handler method, subscribed to event patterns like `vehicle.status.*`, `maintenance.job_card.closed`, `fuel.log.created` — the publishing module needs zero changes, it already calls `register_event()` for its own reasons. This is the "cache invalidate on vehicle status changes, maintenance completed, new trip created" requirement from the vision brief, implemented with infrastructure this codebase already has, not a new pub/sub layer.

**Explicitly not built in this doc's Phase 1–2 (§10):** long-term cross-session "extracted intelligence" (the vision brief's "customer usually ships weekly" style pattern-mining) — that's a genuinely open-ended data-mining feature with no clear v1 shape yet, correctly sequenced last the same way doc 08 §11 sequenced predictive maintenance after rule-based maintenance shipped and accumulated real data first.

---

## 7. Structured output contract

`deployfleet.ai.core.complete()` gains a `response_format` parameter (`"text"` default, unchanged behavior for every existing caller; `"structured"` for Chat) requesting each provider's native JSON-mode/structured-output feature (all three already-integrated providers support one). Shape, deliberately close to the vision brief's own sketch:

```json
{
  "response": "Vehicle ZM-1234 has a rising fuel-consumption trend and 2 recent job cards.",
  "tool_calls": [{"tool": "get_vehicle_summary", "args": {"vehicle_id": 123}}],
  "components": [{"type": "vehicle_card", "vehicle_id": 123}],
  "actions_available": [{"type": "auto", "action": "schedule_service", "label": "Schedule Service"}]
}
```

`components` drives §8's rich rendering; `actions_available` distinguishes `"auto"` (tier 2, §4 — a direct button) from `"approval"` (tier 3 — renders an inline approval card instead). The router validates this against a fixed schema before returning it to the frontend — a malformed structured response degrades to plain `response` text rather than breaking the chat UI, the same "never trust the provider's exact shape" defensiveness `_call_openai_compatible`/`_call_claude` already apply to token-usage parsing.

---

## 8. Rich in-chat components — reuse the existing atom/composite catalog

**Not a new component system.** Every example in the vision brief (a vehicle card, a table, an approval card) maps directly onto `deployfleet_ui`'s existing catalog (doc 18): a "Vehicle Card" is `Card` + `StatusBadge` + the vehicle fields already rendered identically on Fleet Command Center's own expanded-card detail; an "Approval Card" is exactly the Copilot Rail's own existing pending-approval card markup, reused verbatim inside a chat bubble; a table is the same `header-row/table-row` registry pattern used by every registry screen this session built (Parts Registry, Route Manager, etc.). The only genuinely new piece is a small `ChatMessageRenderer` component that reads a message's `rich_payload.components` array (§7) and dispatches to the matching existing atom/composite by `type` — a thin adapter layer, not a new design language. Charts are the one real exception: doc 18 already flags charting as a "needs a real library evaluation" gap (the same gap that kept a Driver Performance Radar out of Phase E's Driver Scorecards slice) — chart-type components stay out of scope until that evaluation happens, not faked with a placeholder.

---

## 9. Frontend: the Chat tab

A new tab inside the existing Copilot Rail panel (`Approvals` | `Chat`), not a second overlay competing with the Rail's own established `Alt+A` entry point. Session list (favorite/archive/rename via the two new session fields, §5) on one side, active conversation on the other, collapsing to a single-pane view below the same 640px breakpoint every other screen in this module uses. Each screen that wires in `useCopilotContext()` (§2) shows a small "Chat is aware of: Vehicle ZM-1234" chip at the top of an active conversation — the one piece of UI that makes context-awareness legible to the user, not just a hidden backend parameter.

---

## 10. Phased rollout — this is not a one-shot build

Sized honestly: doc 08 itself took the "AI action framework" (a narrower scope than this doc) and spread it across a full main-roadmap phase. This is larger. Four phases, each independently shippable and each leaving the product in a coherent, demo-able state — no phase depends on a later phase existing to be useful on its own:

| Phase | Ships | Depends on |
|---|---|---|
| **1 — Read-only chat** | **Built, in two slices, both done.** Slice 1a: Chat tab UI in the Copilot Rail, session persistence (§5 — `feature_id`/`system_prompt` snapshot instead of `agent_id`, per §0's dependency-direction constraint; `favorite`/`archived`), `deployfleet.ai.chat.session.action_send_message()` (a bounded recent-history transcript folded into the existing `complete()` call, not a signature change), agent-scoped session creation, rename/favorite/archive. Slice 1b: `deployfleet.ai.core.complete_with_tools()` plus OpenAI-compatible/Claude tool-calling adapters (§3), the `deployfleet.ai.tool` fixed-dispatch registry in `deployfleet_ai_agents` with the 5 read-only tools, a `_get_reply()` override hook so a tooled session routes through `complete_with_tools()` instead of plain `complete()`, and `useCopilotContext()` (§2) wired into Fleet Command Center + the Dispatch Board, folded into the prompt as a non-persisted `context_note`. | Nothing new for 1a — every piece was additive to already-shipped infrastructure. 1b needed §3's tool-calling plumbing — now built. |
| **2 — Structured responses + rich components** | `response_format="structured"` (§7), `ChatMessageRenderer` (§8) for vehicle/driver/shipment cards and tables, `actions_available` rendering | Phase 1's tool-calling plumbing |
| **3 — Action execution** | The auto-executable tier (§4) with its Phase-2-sized starting allow-list, inline approval cards for tier-3 actions | Phases 1–2; this is the phase that needs the most scrutiny before shipping, given §4's rule change |
| **4 — Memory/context layer** | `deployfleet.ai.entity.summary`/`.company.profile` (§6), event-bus-driven invalidation | Phases 1–3 generating enough real usage to make caching worth the complexity — the same "don't build the advanced layer before there's real data to make it useful" sequencing doc 08 §11 already applied to predictive maintenance |

**Not scheduled in any phase here, flagged as explicitly out of scope for this doc:** cross-session "extracted intelligence" pattern-mining (§6), charts in chat (§8), and voice/multi-modal input — none were load-bearing parts of the vision brief's own numbered priority list, and each is a genuinely open design question on its own.

---

## 11. Open questions, before Phase 1 starts

1. **Confirm the Phase-2-sized auto-executable allow-list (§4)** before any code — this is the doc's own single highest-risk decision and deserves an explicit sign-off list, not an implied one.
2. **Resolved.** §3's first tranche shipped exactly as scoped: Fleet Analyst/Maintenance/Dispatch/Compliance each got tools, Finance and Customer Agent tools were excluded (Finance for the `financial` data-category boundary per §4 criterion 2; Customer Agent for its cross-customer data-isolation concerns, not yet audited for tool access).
3. **Still open.** DeepSeek's/OpenAI's/Claude's tool-calling support was implemented to the well-documented, stable API shapes but has not been verified against a live provider call — this dev environment has no network/API-key access. Verify against the real APIs before relying on this in a demo, the same "verify against the real thing, don't trust the spec PDF" discipline that caught the ZRA endpoint mismatch earlier this project.
4. **Session storage growth** — `deployfleet.ai.chat.message` has no archival/retention policy today; worth deciding before Phase 1 ships whether old sessions need a cron-based cleanup, mirroring `deployfleet.ai.response.cache`'s existing `action_clear_all()`.
