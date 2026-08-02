# 08 — AI Architecture

**Governing principle**, per architecture review, and binding on every AI feature this document describes:

> DeployFleet is an operations platform where AI assists humans, automates repetitive work, detects problems early, and provides intelligence — but every AI capability is modular, permission-controlled, measurable, and optional.

AI is not a standalone chatbot bolted onto the product. It is embedded into fleet management, dispatch, driver management, maintenance, fuel, compliance, finance, customer operations, reporting, and mobile workflows — but every single one of those embeddings must be independently switchable, auditable, cost-tracked, and scoped by who's allowed to see what. This document is the detailed design for that, superseding the brief AI mentions in [01-module-audit.md](01-module-audit.md), [02-reuse-strategy.md](02-reuse-strategy.md), and [04-module-structure.md](04-module-structure.md), which are updated to point here.

## 0. What already exists in the source — verified, not assumed

Given the event-bus discovery in revision 2 (see [02-reuse-strategy.md](02-reuse-strategy.md) §0), this document doesn't take "the AI engine is reusable" on faith. `security_ai_engine`'s actual model code was re-checked specifically against the design principles below, and the result changes how much of this is new build vs. reuse:

| Principle asked for | Already in the source? | Evidence |
|---|---|---|
| Per-feature AI on/off toggles (§1 below) | **Yes, essentially as specified** | `security.ai.config` has `feature_attendance_anomaly`, `feature_risk_profiling`, `feature_billing_auditor`, `feature_roster_optimizer`, etc. — one boolean per feature, exactly the "AI Settings" mockup in the review |
| Provider abstraction / router (§2) | **Yes, shape is right, provider list needs extending** | `security.ai.config.active_provider` is a selection (`claude`/`openai`/`gemini`) with a separate `fallback_provider`; `security.ai.engine.complete()` is the single entry point every feature calls, which dispatches to `_call_provider()` — this **is** the `AI Router` the review's diagram calls for. DeepSeek is not in the provider list yet — see §2. |
| Response caching (§3) | **Yes, close to verbatim** | `security.ai.cache`: `cache_key` (hash of feature + system prompt + user message), TTL via `security.ai.config.cache_ttl_hours`, `hit_count` tracking, an `action_clear_all()` admin action. This is the exact mechanism the review describes ("only send the new fuel event, cache the static vehicle context"), modulo the input granularity being the whole prompt rather than a separately-cached static/dynamic split — see §3 for the one real gap. |
| Usage tracking (§3) | **Yes, close to verbatim** | `security.ai.log`: per-call `user_id`, `feature`, `provider`, `model_name`, `tokens_in`/`tokens_out`, `estimated_cost_usd`, `duration_ms`, `cache_hit`, `state` (success/error). `security.ai.config` computes `monthly_tokens_in/out` and `monthly_cost_usd` from these logs already. |
| Audit trail (§10) | **Partially** | `security.ai.log` captures *what was called and what it cost*, with a request/response preview — but not the review's fuller `ai_action_log` shape (data accessed, suggestion vs. action taken, approval by whom). The gap is specifically the **action** side, not the call-logging side — see §5 and §10. |
| Granular AI permissions (§9) | **No — this is a real gap** | The source's `ir.model.access.csv` for the AI models is standard Odoo ACL: `base.group_system` for config, `base.group_user` for read/write on logs/cache/chat. There is no concept of "a driver can ask about their own trips but not company revenue" — every authenticated user has the same AI access today. This has to be designed fresh; see §9. |
| Action-capable AI with approval gating (§5) | **No — this is a real gap** | Every existing feature (`SecuritySmartRecommendation`, `SecurityPayslipExplain`, etc.) reads and explains; none of them write. There is no suggestion→permission-check→approval→execute→audit pipeline anywhere in the source. This is the single largest genuinely new piece of engineering in this document — see §5. |
| Named "agents" per domain (§6) | **Partially, as feature flags, not personas** | The 10 features are methods/flags on one engine, not six distinct agent identities with their own scope and framing. Reframing them into the review's agent catalog is a relabeling + light restructuring exercise, not new plumbing — see §6. |

**Bottom line for planning purposes:** the AI *foundation* (provider routing, caching, usage/cost tracking, feature toggles) is roughly 70% built already and needs DeepSeek added plus a cheap/expensive model tier per feature. The AI *action framework* and *granular permission model* are genuinely new and are the real engineering lift in this document — size the roadmap accordingly (see §11).

## 1. Module structure

Supersedes the "Intelligence" section of [04-module-structure.md](04-module-structure.md):

| Module | Depends | Purpose |
|---|---|---|
| `deployfleet_ai_core` | `deployfleet_event_bus`, `web` | Provider abstraction/router, `deployfleet.ai.config` (global + per-feature toggles), `deployfleet.ai.cache`, `deployfleet.ai.usage` (renamed from the source's `security.ai.log`, extended per §3), the assistant chat panel. **Renamed from the earlier `deployfleet_ai`** per review's explicit naming — this module is infrastructure, the way `deployfleet_event_bus` is, and the name should say so. |
| `deployfleet_ai_permissions` | `deployfleet_ai_core`, `deployfleet_security` | The genuinely new piece: per-role/per-user AI access scoping and token budgets — see §9. Kept as its own module rather than folded into `deployfleet_ai_core` because it depends on `deployfleet_security`'s role groups, and `deployfleet_ai_core` shouldn't have to depend on the full security/role module just to run a provider call. |
| `deployfleet_ai_actions` | `deployfleet_ai_core`, `deployfleet_ai_permissions`, `deployfleet_event_bus` | The suggestion→approval→execute→audit pipeline (§5) — the other genuinely new piece. Separate module because it's meaningfully riskier code (it writes to the database) than the read-only analysis features, and should be independently disableable — a customer can run DeployFleet with AI *analysis* on and AI *actions* off. |
| `deployfleet_ai_agents` | `deployfleet_ai_core` | The six agent personas (§6) as **data records, not separate installable modules** — see §6 for why. |
| `deployfleet_ai_whatsapp` | `deployfleet_hr`, `deployfleet_customer`, `deployfleet_trip`, `deployfleet_ai_core`, `deployfleet_ai_agents` | WhatsApp check-in / breakdown reporting / customer shipment queries — direct successor to `security_ai_whatsapp_bridge`, now also capable of triggering `deployfleet_ai_actions` (e.g., a driver's WhatsApp breakdown report creating a real breakdown ticket, gated the same way any other AI action is). |

This changes the Intelligence-layer module count in [04-module-structure.md](04-module-structure.md) from 2 to 5 — reflected there.

## 2. Provider abstraction and DeepSeek strategy

The source's router shape is sound and is kept:

```
Caller (any feature/agent)
        |
        v
deployfleet.ai.core.complete(feature, agent, system_prompt, user_message, context)
        |
        v
Provider Router  ──── reads deployfleet.ai.config: active_provider, per-feature model tier
        |
   ┌────┼────┬─────────────┐
   v    v    v             v
DeepSeek OpenAI  Claude   (local model — future extension point, not built now)
```

**DeepSeek becomes the default/primary provider**, added alongside the existing Claude/OpenAI/Gemini options rather than replacing them — the abstraction's whole value is that no feature code cares which provider answers it. Rationale for DeepSeek as default, per review: low cost for a commercial SaaS product serving price-sensitive Zambian trucking companies, strong reasoning models, and native prompt-caching support that pairs well with §3.

**Two-tier model routing per feature**, a genuine addition beyond what the source has (the source picks one model per provider, not per call complexity):

| Tier | Example DeepSeek model | Used for |
|---|---|---|
| Cheap / routine | `deepseek-chat` | Trip summaries, payslip explanations, routine anomaly flags — high volume, low stakes |
| Expensive / reasoning | `deepseek-reasoner` | Dispatch optimization across a full day's trips, financial forecasting, multi-constraint fleet allocation — low volume, high stakes |

Each feature/agent in `deployfleet.ai.config` gets a `model_tier` selection (`cheap` / `reasoning`), not just a provider choice — this is a new field relative to the source's `security.ai.config`, not a new architectural layer.

**Data-governance note, carried into [06-risks-and-recommendations.md](06-risks-and-recommendations.md):** routing business data through any third-party hosted model (DeepSeek included) means that data leaves the customer's infrastructure. The provider abstraction should support restricting specific features (payroll/salary data, for instance) to "no AI" or to a specifically-approved provider per company, not just a single global on/off switch — this is a permission-model requirement (§9), not just a provider-selection one.

## 3. Cost architecture: caching and usage tracking

Both mechanisms below already exist in the source (§0) — this section describes what changes, not what's built from zero.

**Caching — one real gap to close.** The source's `security.ai.cache` hashes the *entire* prompt (feature + system prprompt + user message) as one cache key. The review's example (cache the static vehicle profile, only send the new fuel event) implies a **split cache**: a long-lived cache entry for the static/slow-changing context (vehicle spec, maintenance history, service intervals) separate from the fast-changing delta (today's fuel reading) that actually varies per call. Implement this as two cache tiers in `deployfleet_ai_core`:

- `deployfleet.ai.context.cache` — long TTL (days), keyed on entity + context version (e.g., vehicle ID + last-modified timestamp of its profile), reused across many calls about the same entity.
- `deployfleet.ai.response.cache` — the source's existing short-TTL, full-request-hash cache, kept as-is for exact-repeat queries.

**Usage tracking — rename and extend, don't rebuild.** `security.ai.log` becomes `deployfleet.ai.usage`, keeping every existing field (tokens in/out, estimated cost, cache-hit flag, duration, provider/model) and adding:

- `agent` (which of the six agents in §6 made the call, distinct from `feature`)
- `company_id` — the source's model doesn't scope by company; a multi-tenant/multi-company DeployFleet install needs per-company cost attribution for billing AI usage back to the customer, which is explicitly one of the review's stated goals for this table ("billing AI usage, detecting abuse, optimizing prompts").
- A **token budget** concept, which doesn't exist in the source at all today (only `max_tokens` per single call): `deployfleet.ai.budget` records a monthly token/cost ceiling per company (and optionally per user), checked before a call is made — the source has no equivalent of this, so this is new.

## 4. Global AI action framework (UI pattern)

Every major record view gets a consistent "Ask AI" affordance with a small, fixed verb set — Analyse / Explain / Suggest / Create / Update / Optimise — rather than a free-text box on every screen. This keeps the surface predictable for users and keeps the permission/audit model in §5/§9 tractable (a fixed verb set is checkable against a permission table; an open-ended chat box per-record is not). The existing AI chat panel (`security.ai.chat.session`/`message`, kept as `deployfleet.ai.chat.session`/`message`) remains as the free-form entry point *in addition to* these per-record verbs, not instead of them.

Read-only verbs (Analyse, Explain, Suggest) call `deployfleet_ai_core` directly. Write-capable verbs (Create, Update, Optimise-and-apply) always route through `deployfleet_ai_actions` (§5) — never directly to a model write.

## 5. Action-capable AI: the approval pipeline is non-negotiable

This is the one principle in this document to treat as a hard constraint, not a design preference, because it's the difference between "AI assistant" and "a service account with unaudited write access to the ERP":

```
AI Suggestion
     |
     v
Permission Check  (deployfleet_ai_permissions — can this user/role trigger this action type?)
     |
     v
User Approval     (the human sees exactly what will be written, not just a summary)
     |
     v
Execute Action    (deployfleet_ai_actions writes via the normal ORM, no bypass of existing
     |              validation/constraints — an AI-proposed maintenance record is subject to
     |              exactly the same constraints a human-entered one would be)
     v
Audit Log         (deployfleet.ai.action.log — see §10)
```

Model shape for `deployfleet_ai_actions`:

- `deployfleet.ai.action.request` — `agent_id`, `action_type` (e.g. `create_maintenance_schedule`), `target_model`, `proposed_vals` (JSON), `state` (`draft` → `pending_approval` → `approved`/`rejected` → `executed`/`failed`), `requested_by`, `approved_by`, `executed_at`, `source_context` (what triggered this — a WhatsApp message, a dashboard click, a scheduled agent run).
- No action executes without a `state` transition through `approved` by a human with the right permission — there is no "auto-execute" mode in v1 of this design, full stop. If a future version wants AI to auto-execute low-risk, high-confidence actions without a human in the loop, that's a deliberate later decision requiring its own sign-off, not a default.

## 6. Agent catalog

Implemented as **data records in `deployfleet_ai_agents`**, not six separate installable modules. Rationale: all six share the same provider router, cache, usage tracking, and permission engine in `deployfleet_ai_core`/`deployfleet_ai_permissions` — an agent is really a named bundle of (system prompt template, allowed action types, default model tier, data-access scope), which is configuration, not a distinct code module. This also matches the shape the source already has (one `security.ai.engine` AbstractModel, ten feature flags) — the review's agent framing is a restructuring of that shape into clearer, more legible personas, not a new plumbing layer.

| Agent | Responsibilities | Maps to existing/planned modules |
|---|---|---|
| Fleet Analyst | Utilization, vehicle performance, cost analysis | `deployfleet_vehicle`, `deployfleet_fuel`, `deployfleet_reports` |
| Dispatch Agent | Trip assignment suggestions, route optimization, driver matching | `deployfleet_dispatch`, `deployfleet_route` |
| Maintenance Agent | Service prediction, failure detection, workshop planning | `deployfleet_maintenance`, `deployfleet_workshop`, `deployfleet_breakdown` |
| Finance Agent | Invoice analysis, profitability, payment risk | `deployfleet_billing`, `deployfleet_accounting` |
| Compliance Agent | Expired documents, regulatory risk, inspection schedules | `deployfleet_compliance`, `deployfleet_vehicle_compliance`, `deployfleet_dispatch_compliance` |
| Customer Agent | Shipment tracking, customer questions, delivery updates | `deployfleet_shipment`, `deployfleet_trip`, `deployfleet_customer_portal` |

Each agent's data-access scope is enforced by `deployfleet_ai_permissions` (§9), not by convention — the Customer Agent, for instance, must be structurally incapable of returning payroll data even if a cleverly-worded prompt asks it to, because its permission scope never included that model in the first place.

## 7. AI-augmented dashboards

Every dashboard from [02-reuse-strategy.md](02-reuse-strategy.md) §2 (Fleet Ops Dashboard, Billing Command Center) gets an AI intelligence layer alongside its raw metrics — not replacing the numbers, annotating them:

```
Fleet Utilization: 82%        →  ⚠ Fuel cost increased 18% this month
Fuel Cost: K250,000               Cause: three trucks consuming above average
Trips: 342                        Recommended: inspect vehicles 12, 17, 21
```

These annotations are Fleet Analyst / Maintenance Agent outputs (§6) surfaced inline, using the same cache (§3) a dashboard refresh would otherwise re-spend tokens on every page load — the context-cache split in §3 exists specifically so a dashboard that hasn't changed doesn't re-query the AI provider on every view.

## 8. WhatsApp integration

`deployfleet_ai_whatsapp` (successor to `security_ai_whatsapp_bridge`) handles both inbound patterns from the review:

- **Driver-reported events** ("Truck 14 broke down") → parsed into structured fields (driver, vehicle, location, issue) → **routed through `deployfleet_ai_actions`** to create a breakdown ticket, not written directly — this is exactly the kind of AI-initiated write §5's approval pipeline exists for, though for a driver-originated breakdown report a fast-tracked/pre-approved action type is a reasonable design choice (a dispatcher confirming "yes, that's a real breakdown" within the app is arguably still faster than requiring approval before the ticket even appears) — flagged here as an implementation-time policy decision per action type, not a blanket exception to §5's rule.
- **Customer queries** ("Where is my shipment?") → read-only, served by the Customer Agent directly against `deployfleet_shipment`/`deployfleet_trip`, no approval step needed since nothing is written.

## 9. AI security and permissions — the genuinely new subsystem

Nothing in the source enforces this today (§0). `deployfleet_ai_permissions` introduces:

- **Per-role feature/agent access** — e.g., a driver can query the Dispatch Agent about their own trips and the Fleet Analyst about their own vehicle, but not the Finance Agent at all; a dispatcher can access trip/driver/vehicle-scoped agents but not full financial detail; an owner has unrestricted access. This mirrors, but is distinct from, Odoo's model-level ACLs — an AI query permission is "can this role ask this *kind* of question," which is a coarser and different concern than "can this role read this *model*."
- **Row-level scoping within a permitted feature** — a driver permitted to query the Dispatch Agent must be scoped to their *own* trips, not the whole company's, which is a data-scope rule the AI layer has to enforce on top of (not instead of) Odoo's own record rules, since the AI's answer is synthesized text, not a raw recordset a record rule would naturally filter.
- **Token/cost budgets per company and optionally per user** (§3), checked before a call proceeds, not just reported after the fact — the source's usage tracking is entirely retrospective (compute stats from logs) with no pre-call gate.
- **Data-sensitivity flags per feature** — see §2's data-governance note; a company should be able to mark payroll-adjacent features as "no external AI provider" without turning off AI entirely.

## 10. Audit trail

Two logs, not one, reflecting the two kinds of thing the platform's AI does:

- `deployfleet.ai.usage` (§3, extends the source's `security.ai.log`) — every AI *call*, whether read-only or action-related: who, what feature/agent, tokens, cost, cache hit, success/error.
- `deployfleet.ai.action.log` (new, companion to `deployfleet.ai.action.request` in §5) — every AI *action* specifically: `user`, `prompt`/trigger context, `data_accessed`, `suggestion`, `action_taken`, `approved_by`, `timestamp`. This is the review's `ai_action_log` shape exactly, and is new relative to the source, which has no action-taking AI at all to audit.

## 11. AI-specific phased roadmap, reconciled against the main roadmap

The review's own 4-phase AI roadmap (Foundation → Operational Intelligence → Automation → Advanced Intelligence) is adopted, but mapped explicitly against the main 5-phase roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md) rather than treated as a separate timeline — two roadmaps that don't reference each other is how "when does AI ship" quietly becomes an undocumented argument later.

| AI phase | What it covers | Lands during main roadmap phase | Why |
|---|---|---|---|
| **AI Foundation** | `deployfleet_ai_core` (provider router + DeepSeek + caching + usage tracking, per §0–§3), `deployfleet_ai_permissions` skeleton, basic assistant chat UI | **Phase 0–1** (Operational Foundation), earlier than the main roadmap's original Phase 5 placement | Same logic as promoting `deployfleet_event_bus` to Phase 0: foundation modules are cheap to build early and expensive to retrofit under a pile of features that assumed they didn't exist. Since ~70% of this already exists in the source (§0), the marginal cost of building it in Phase 0–1 instead of Phase 5 is small. |
| **AI Operational Intelligence** | Fleet Analyst and Maintenance Agent read-only analysis, Compliance Agent alerts | **Phase 2–3** (Cost Control, Compliance) | Needs real trip/fuel/compliance data flowing from Phase 1 to be useful — an analysis feature running on seed data is a demo, not a product, per [05-implementation-roadmap.md](05-implementation-roadmap.md)'s existing caution about this. |
| **AI Automation** | `deployfleet_ai_actions` (the approval pipeline), WhatsApp assistant with action-capable intents | **Phase 4** (Customer Platform) | The approval pipeline needs `deployfleet_security`'s finished role model and enough real operational volume that automating repetitive actions is worth the (real, and non-negotiable per §5) engineering cost of building it safely. |
| **AI Advanced Intelligence** | Predictive maintenance (ML-based failure forecasting), fuel anomaly detection, dispatch/route optimization, financial forecasting | **Phase 5** (Intelligence) | **Important distinction, not a conflict**: [05-implementation-roadmap.md](05-implementation-roadmap.md) Phase 2 already ships `deployfleet_maintenance` — but that's *rule-based* preventive maintenance (odometer/calendar triggers), not AI-*predicted* maintenance. The rule-based version ships early because it's cheap and valuable immediately; the AI-enhanced version (forecasting failure likelihood from consumption/fault patterns) is correctly sequenced last, once there's enough historical maintenance/breakdown data across Phases 1–4 for a prediction to be better than the rule-based baseline it's improving on. |

**Net effect on [05-implementation-roadmap.md](05-implementation-roadmap.md):** Phase 0 gains "extract/build `deployfleet_ai_core`'s foundation alongside the event bus"; Phase 5 stays the home of the *advanced* AI features but is no longer where AI *starts* — the assistant chat panel and basic per-feature toggles should be visible to users from Phase 1 onward, even if most feature flags are off until their data dependencies exist.

## 12. Open questions specific to AI (feed into [06-risks-and-recommendations.md](06-risks-and-recommendations.md))

1. Is DeepSeek's API acceptable for customer financial/payroll data under the target customers' data-handling expectations, or should sensitive features be restricted to a different provider (or no AI) by default until confirmed?
2. Should the WhatsApp-driven breakdown-ticket action (§8) be pre-approved by policy, or must every driver-reported breakdown wait for human confirmation before a ticket is created? This is a real product-usability-vs-safety tradeoff, not a technical one.
3. What's the default token/cost budget per company for the MVP release, and who gets alerted when it's approached — this needs an answer before `deployfleet_ai_core` ships, not after the first customer hits it.
