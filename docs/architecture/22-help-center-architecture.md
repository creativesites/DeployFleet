# 22 — Help Center Architecture

## 0. What already exists — reuse audit, not assumed

Before this work, DeployFleet had zero help/documentation surface anywhere in the product (confirmed: no hits for any help-related code across `deployfleet_ui` or any business module). New users — trucking-company owners, dispatchers, HR staff, drivers, workshop managers, largely non-technical and with no prior ERP experience — had no in-app way to learn how the system works, despite ease-of-use being a stated selling point and a direct driver of demo win rate (CLAUDE.md §10).

What already existed and was reused as-is, not rebuilt:

- **The design-system/component library** (`deployfleet_ui`) — Button, Card (`workspace`/`command` layer), StatusBadge, ErrorBanner, the tab/filter-chip/accordion patterns every prior domain's workspaces already established.
- **The Command Palette / Mega Menu / Launcher navigation trio** — the Help Center is wired into all three rather than inventing a fourth navigation surface.
- **The Copilot Rail's context-store pattern** (`copilot_rail/copilot_context.js`) — `help_trigger/help_context.js` is a deliberate structural twin, not a new pattern.
- **`fields.Html(sanitize=True)`** — Odoo's own standard rich-content field, the same mechanism Odoo's Knowledge/Website apps use, with a ready-made authoring widget. No markdown dependency was introduced; none exists anywhere in this codebase's asset bundle.
- **`mail.thread`** on `deployfleet.help.article` — a free, real change-history/audit trail via Odoo's own chatter, covering "future versioning" without a bespoke snapshot model.
- **The `<odoo noupdate="1">` seed-data convention** — the same mechanism `deployfleet_leave_type_data.xml` and every other module's permanent required content uses. `post_init_hook` was deliberately not used; that mechanism is reserved in this codebase for exactly one case, `deployfleet_demo_zm`'s optional, environment-specific, fictional demo dataset. Help Center content is neither optional nor environment-specific.

## 1. Scope — what shipped vs. what the original spec asked for

The user's request was extremely detailed and spans a full-domain-sized feature. This doc records what was actually built as v1, and names what is architected-for but deliberately deferred, per this project's own standing discipline (every prior domain scoped and named its own deferrals rather than silently dropping requested items).

**Built:**

1. **Welcome / Getting Started** — a landing page (`home` section) plus a Getting Started guide article.
2. **Learn the Business Workflow** — three seeded step-diagrams (Customer→Contract→Shipment→Dispatch→Trip→Delivery→Invoice→Payment; Vehicle→Inspection→Maintenance Schedule→Workshop Job Card→Parts Used→Back In Service; Hire Driver→Documents→Assign Vehicle→Trips→Performance→Payroll), rendered by the new `DeployfleetWorkflowDiagram` signature widget.
3. **Module Guides** — one article per named module (Fleet, Dispatch, Drivers, HR, Finance, Compliance, Workshop, AI), each structured What it does / Why it exists / Typical daily tasks / Best practices / Common mistakes / Related areas, written in plain trucking-business language.
4. **Search** — a backend-ranked search (title-match-first across title/summary/body/tags) wired into the Help Center's own search box, the Command Palette, and (implicitly, via quick links) the persistent Help Trigger.
5. **FAQ** — 7 seeded articles covering the example questions given (assigning a truck, changing a driver, payroll, maintenance schedules, compliance documents) plus two more.
6. **Troubleshooting** — the 5 named examples, each with plain-English likely causes.
7. **AI Copilot Help** — one article covering the 4 named example prompts, approvals, and reports/analysis.
8. **Contextual Help** — a two-tier mechanism (§3) with an explicit "Help" button on three pilot workspaces (Fleet Command Center, Workshop Board, Payroll Center) and an ambient corner trigger present everywhere.
9. **Role-based relevance (partial)** — `deployfleet.help.article.role_group_ids` (m2m `res.groups`) exists on the data model so an article can be tagged relevant-to-a-role, but no frontend filtering/sorting by the current user's role reads it yet — the field is real, populated for none of the seeded content, and the frontend consumption is deferred.
10. **First-Time Experience** — a real "First-Time Setup" checklist (Welcome → add first vehicle → add first driver → create first shipment → assign it → congratulations) with per-user progress tracking, rendered on the Help Center home and surfaced via a dismissible strip on Mission Control.

**Explicitly deferred, not silently dropped:**

- **Interactive, element-highlighting guided walkthroughs** ("Take me through creating my first trip") — no DOM-spotlight/tour mechanism exists anywhere in this codebase, and building one is materially riskier and larger than everything else in this doc. A real, separately-scoped future feature.
- **Video/GIF/screenshot embedding** — no speculative schema fields were added for this (see §2's reasoning on what was and wasn't spec'd ahead of need). Adding a `video_url`/`video_embed` field to `deployfleet.help.article` later is a risk-free additive migration.
- **AI-answers-from-Help-Center-content** — Copilot does not yet retrieve from this content. §6 sketches the integration point; it is documentation only, not built.
- **Contextual Help buttons on all ~40 workspaces** — three screens (one per Fleet/Operations/HR-Finance) were wired as a bounded pilot, the same "pilot on a few screens, prove the pattern, extend later" discipline already used for `useCopilotContext()`.
- **Role-based frontend filtering** — the data model supports it (`role_group_ids`); the Help Center doesn't yet read the current user's groups to reorder or filter content.
- **Localization/translation** — no `translate=True` was added preemptively; Odoo's own translation mechanism needs zero schema change to adopt later.
- **Customer-specific documentation** — no schema exists for this; not requested with enough concreteness to design against yet.

## 2. Data model

New module: `deployfleet_help`, depending only on `deployfleet_security` (not `deployfleet_core` — a knowledge base doesn't need the sequence-code mixin every operational model uses). All frontend/navigation code lives in `deployfleet_ui`, matching how `deployfleet_leave` and every other content-owning module is split from its UI.

| Model | Purpose |
|---|---|
| `deployfleet.help.category` | Browse category. `parent_id` (self) lets "Module Guides" hold 8 children without each becoming a top-level category. `context_key`/`domain_key` are the two deep-link keys §3's resolution algorithm reads. |
| `deployfleet.help.tag` | Simple named tag, searchable. |
| `deployfleet.help.article` | The single content model for guides, module guides, FAQ, and troubleshooting — one model, not four, distinguished by `content_type` (Selection: `guide`/`module_guide`/`faq`/`troubleshooting`). All four are structurally "a title plus a plain-language body"; splitting them would duplicate search/tagging/related-article/role-relevance/audit-trail machinery for no benefit. `body` is `fields.Html(sanitize=True)`. `_inherit = ["mail.thread"]` gives a free, real audit trail. `search_help()` (recordset-returning, for internal Python callers) and `search_help_ids()` (its RPC-facing wrapper — see §5) implement ranked search. |
| `deployfleet.help.workflow` / `.workflow.step` | Structured data behind the step-diagrams. A step's `related_model` is a soft-coupled string (matching this codebase's universal `orm.searchRead(model_string, ...)` convention), deliberately left unset where no backing model exists (e.g. the Inspection step — no inspection model exists anywhere in the 43-module backend, a fact already established during the Maintenance Planner build). |
| `deployfleet.help.checklist` / `.checklist.item` | The First-Time Experience checklist as real data, not hardcoded UI — a future role-specific second checklist is just a new record. |
| `deployfleet.help.checklist.progress` | Per-user completion tracking (`user_id` + `checklist_item_id` unique together), `ir.rule`-scoped to the caller's own rows. Items are user-toggled, not auto-detected from real activity ("has this user actually created a vehicle yet?") — that inference is real, useful, per-item-bespoke logic and a named future enhancement, not built here. |

**Deliberate design decisions, and why:**

- **No `company_id` anywhere in this module.** Help content documents how to use the product, which is identical for every company on a deployment — a genuine, reasoned contrast with the just-completed C-01 multi-company-isolation audit, not an oversight.
- **No speculative schema for translation/video/customer-scoping.** Both are risk-free additive migrations later. The *relational* shape (an open `content_type` Selection, stable `slug`/`context_key` fields, real M2M tag/related-article models) was decided now, because retrofitting relational shape is not risk-free the way adding a nullable field is.
- **`slug` is a separate stable key from `name`.** Deep-links (`context_key`) and category/workflow identity are keyed by slug, not by display name or database id, so renaming an article's title never breaks a stored link.

## 3. Contextual-help resolution algorithm

Every entry point that opens the Help Center pre-scoped to a topic funnels through the same resolution order, implemented once in `help_center.js`'s `resolveContext()`:

1. **`params.article_id`**, when set, wins outright — the caller already knows the exact article (only the Command Palette's Help results and the ambient corner trigger's contextual link use this; see §4 on why these two use an inline action descriptor rather than a stored one).
2. Else **`params.context_key`** is checked against every article's own `context_key` — an article-level match wins.
3. Else the same key is checked against every **category's** `context_key`.
4. Else the same key is checked against every category's **`domain_key`** (a broader fallback — useful if a caller only knows "this is a fleet-related screen," not a specific Help topic).
5. Else the Help Center opens on `home`.

A category resolved via steps 3/4 that has **exactly one article** opens that article directly rather than a one-item list — this is why Getting Started, AI Copilot Help, and every individual Module Guide child category behave as if they were single articles even though they're modeled as categories.

## 4. Frontend architecture

**One workspace, many sections**, the same pattern already used by Compliance Center / Copilot Console: `deployfleet_ui.help_center` is a single `ir.actions.client` with an internal `state.activeSection` router (`home` / `workflows` / `workflow_detail` / `guides` / `category` / `article` / `search`), not one action per section.

**Layer switching within one screen**: `home` uses Command Layer light glass (an orientation/launch surface, per doc 16 Principle 1); every other section is flat Workspace Layer once the user has drilled in to actually read something. This is a deliberate, documented in-screen exception — the same class already granted to the Dispatch Board.

**New shared signature widget**: `components/workflow_diagram/` (`DeployfleetWorkflowDiagram`), added to doc 18 §5's catalog — a horizontal (desktop) / vertical (mobile) numbered step timeline, data-only (`steps` prop), reusable for any future step-sequence, not just Help Center workflows.

**Navigation wiring, four surfaces:**

1. **Mega Menu** — a 7th domain (`help`), six tiles mirroring the Help Center's own home cards, each a separate stored `ir.actions.client` record sharing the `deployfleet_ui.help_center` tag but baking in a different `params.context_key` — the exact "one tag, many action records" pattern already established by the six original Mega Menu domains.
2. **Launcher** — one grid entry, `Alt+K` badge, reusing the `--df-color-info`/`-bg` status-semantic hue rather than inventing a new one (Help is cross-cutting/informational, not a new operations domain).
3. **Command Palette** — a second, separate `command_provider` block (not a `RECORD_SEARCH_TARGETS` row, since it needs ranked search, not a plain `ilike` filter), opening the matched article via `params.article_id`.
4. **Persistent Help Trigger** (`help_trigger/`) — a new, always-mounted corner button (bottom-left — the one uncontested corner; the Launcher trigger owns bottom-right, the Copilot Rail's docked tab owns the vertically-centered right edge), `Alt+K` global hotkey, a small flyout with quick links plus a contextual "Help for `<workspace>`" link when the ambient store below has been set.

**Two-tier contextual help, both piloted on the same three screens** (Fleet Command Center, Workshop Board, Payroll Center):

- **Tier 1 — ambient.** `help_trigger/help_context.js` exports `helpContextStore`/`useHelpContext()`, a structural twin of `copilot_rail/copilot_context.js`: a workspace opts in with one `setup()` line (`useHelpContext().setContext(contextKey, label)`), and the persistent corner trigger becomes contextual for near-zero marginal cost. Unlike the copilot context store (which tracks a specific *record*), this one tracks a *workspace*, set once at mount, not per-interaction.
- **Tier 2 — explicit.** A "Help" button in each pilot workspace's header, calling a pre-baked, context-scoped stored action directly (`deployfleet_ui.action_deployfleet_help_center_fleet` etc.) — no inline descriptor needed here, since the three pilot workspaces are a fixed, small, known set.

**Inline `ir.actions.client` descriptors — a considered, first-time deviation.** Every prior `doAction()` call in `deployfleet_ui` targets either a stored action by xmlId, or an inline `ir.actions.act_window` descriptor (long-proven throughout this module). This is the first use of an inline **client**-action descriptor (`{type: "ir.actions.client", tag: "deployfleet_ui.help_center", params: {...}}`), used in exactly two places: the Command Palette's Help results and the corner trigger's contextual link. Both target genuinely dynamic content (an arbitrary matched article; whichever of the three pilot workspaces is currently open) that cannot be pre-enumerated into stored records the way the six Mega Menu tiles' fixed context keys can. The action manager resolves this descriptor shape through the same standard, well-documented dispatch path as any stored client action — a materially lower-risk pattern than, say, patching Odoo's own `NavBar` DOM structure, which this project has twice deliberately declined to do (the Launcher's own scope correction, doc 16 §3.2).

## 5. Search architecture

`deployfleet.help.article.search_help(query, limit=20)` does ILIKE search across title/summary/body/tags, title-match-first ranked. Correctly sized for the content volume this module actually seeds today (well under 30 articles) — a Postgres full-text-search upgrade is a documented future enhancement, not built speculatively now, since no full-text-search precedent exists anywhere else in this codebase either.

**A real bug found and fixed while wiring the frontend, not a design footnote:** `search_help()` returns a recordset. A bare recordset is not JSON-serializable, and would have raised the moment any JS caller actually invoked it over RPC — a class of bug this codebase has hit before (methods that work perfectly under a direct-Python test but break at the RPC boundary, since the existing test suite's own `TransactionCase` calls never cross that boundary). Fixed by adding `search_help_ids(query, limit=20)` — a thin wrapper returning `.ids` — as the one RPC-facing entry point every JS caller (the Help Center's own search box, the Command Palette provider) actually calls. `search_help()` itself is unchanged and keeps its recordset return, since that's the more natural contract for internal Python callers and its own existing tests.

## 6. Future AI-retrieval integration — sketch only, not built

Doc 21 (§10, Phase 1b) already gave `deployfleet_ai_agents` a working tool-calling registry (`deployfleet.ai.tool`, a fixed-dispatch Python dict keyed by `key`) and five read-only tools scoped to specific agents. The natural, structurally-ready integration point for "Copilot should answer questions directly from Help Center content" is a sixth tool:

```
search_help_articles(query: str) -> list[{title, summary, url_or_id}]
```

implemented in `deployfleet_ai_agents` (never in `deployfleet_ai_core`, preserving the same one-way dependency direction every other tool already respects), calling `deployfleet.help.article.search_help_ids()` and returning a small, structured result set — **not** dumping the whole knowledge base into the LLM's context, which is exactly the retrieval discipline the user's own request specified ("via structured retrieval, not by dumping the whole knowledge base into the LLM").

This is documented as the integration point, not implemented, for the same reason every other doc-only sketch in this codebase stays doc-only until a concrete session asks for it: `deployfleet_help` would need to become a manifest dependency of `deployfleet_ai_agents` (a new, real coupling, currently absent), and doc 21 §11's own open item about live-provider tool-call verification (no network/API-key access in this dev environment) still applies to any new tool exactly as much as the five that already exist.

## 7. Phased rollout — what was actually built, in order

1. **Backend** — the full `deployfleet_help` module: models, security, seed content (workflows, guide/module-guide/FAQ/troubleshooting/AI-help articles, the setup checklist), tests. Found and fixed one real gap along the way: `deployfleet.help.category`'s "Module Guides" parent had no `context_key` of its own (added in the navigation-wiring batch, once it became clear the Mega Menu's "Module Guides" tile needed one).
2. **Frontend core** — the Help Center screen itself (all sections except the checklist), the `DeployfleetWorkflowDiagram` widget, backend-ranked search — reachable via its own top-level menu item only, not yet wired into any shared navigation surface.
3. **Navigation & contextual integration** — the 7th Mega Menu domain, the Launcher entry, the Command Palette provider, the persistent Help Trigger + `help_context.js`, and the two-tier contextual "Help" buttons on the three pilot workspaces.
4. **Onboarding checklist UI** — checklist rendering + progress toggling inside the Help Center's `home` section, plus the one existing-screen touch in this whole feature: Mission Control's dismissible "Finish setting up DeployFleet" strip.
5. **Documentation** — this doc, plus the CLAUDE.md running-log entry and §2 doc-index row.

Each batch was verified (JS syntax, XML well-formedness, a full OWL-compiler pass, the full `web.assets_backend` SCSS bundle compiled via libsass, manifest parse checks, cross-checking every new `actionXmlId` string against its defining record) and committed/pushed separately — the same per-batch discipline every prior domain in this project used, not one large unreviewable commit.

## 8. Open questions / not yet closed

- **Not verified in a live browser.** Same standing caveat as every `deployfleet_ui` screen shipped since Phase A — syntax-valid and structurally-correct is not the same as rendering correctly. The Help Center is a genuinely novel screen shape for this module (its first `fields.Html` rendering via OWL's `markup()`, its first inline `ir.actions.client` descriptor usage) and is a strong candidate for the next redeploy-and-click-test pass, alongside the accumulated backlog from every domain since early in the Experience Architecture work.
- **Role-based content filtering is data-ready but not consumed.** `role_group_ids` exists and is queryable; no seeded article uses it yet, and the frontend doesn't read the current user's groups to filter or reorder anything.
- **Interactive guided walkthroughs remain unbuilt**, and are a materially larger, separately-scoped effort — no DOM-spotlight/tour mechanism exists anywhere in this codebase to build on.
- **The `search_help_articles` AI tool (§6) is documented, not implemented** — the next natural step once a session is explicitly scoped to extend the Copilot Rail's tool catalog again.
- **Contextual Help buttons cover 3 of ~40 workspaces.** Extending tier 2 to more screens is mechanical (one `useHelpContext().setContext()` call plus one stored action record per screen) but was deliberately not done broadly in this pass, matching how `useCopilotContext()` itself was piloted narrowly before any wider rollout was requested.
