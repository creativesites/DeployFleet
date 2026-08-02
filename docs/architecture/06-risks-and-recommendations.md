# 06 — Risks and Recommendations

*Revision 2 — the vehicle-architecture question (risk #2) is now resolved per architecture review (delegation inheritance over `fleet.vehicle` — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2) and removed from the open-questions list below; a new risk (#6) covers the event-bus subscriber-coupling defect found during review; [07-domain-model-erd.md](07-domain-model-erd.md) is now the concrete deliverable risk #4 was asking for, still pending real-world validation.*

## Hard risks

### 1. `security_dogforce_data` must never be forked, referenced, or partially copied

This module (71,419 lines) loads a real security company's actual production data — guards, clients, contracts — from XLSX via a post-install hook. It is not "technical debt," it's a live business's operational data sitting in a codebase. It has zero architectural value to DeployFleet (it's not a reusable pattern, just a data loader pointed at specific files) and carries real risk if it ever ends up in a new commercial product's repository, even privately: it's someone else's client data, someone else's business, and not something a fork of this scope should be anywhere near. **Recommendation: exclude it explicitly and permanently — don't "review it later," don't keep a copy "for reference."** The scratch clone of the source repository used to produce this analysis should be deleted once this planning work is accepted, not kept around locally.

### 2. The `fleet.vehicle` naming collision — resolved, but worth understanding why

Odoo's native Fleet app already defines `fleet.vehicle` and related models. **This is now resolved**: `deployfleet.vehicle` uses Odoo's delegation inheritance (`_inherits = {"fleet.vehicle": "fleet_vehicle_id"}`) rather than either reinventing a standalone model or welding fields directly onto the core table — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2 for the pattern and rationale. It's kept here as a risk entry, downgraded from "open decision" to "resolved decision to not silently deviate from during implementation" — the failure mode now is someone writing `deployfleet_vehicle` later without knowing this was decided, and reaching for plain `_inherit` or a from-scratch model instead. Point implementers at the ADR from Phase 0 (see [05-implementation-roadmap.md](05-implementation-roadmap.md)) rather than re-relitigating it per module.

### 3. Compliance and driver rest-hour rules carry more legal weight in trucking than the source treated them

In DeployGuard, `security_compliance_roster` (document-expiry-blocks-dispatch) and rest-rule enforcement in `security_shift_planner` were real but secondary features — a guard working past their rest window is a labor-practice problem. In trucking, a driver working past a rest/hours limit, or a vehicle dispatched without valid insurance or roadworthiness, is a safety and regulatory liability with sharper legal consequences (accidents, fines, insurance voidance, license revocation). The source codebase's own `KNOWN_ISSUES.md` lists rest-rule and understaffing enforcement as "P2 — Operations completeness," i.e. nice-to-have. **Recommendation: for DeployFleet, treat hard-constraint enforcement in `deployfleet_dispatch_compliance` and driver rest rules in `deployfleet_dispatch`'s scoring engine as core, non-optional, Phase 3 scope — not a P2 backlog item** — regardless of how the source prioritized the equivalent feature. See [05-implementation-roadmap.md](05-implementation-roadmap.md) Phase 3.

### 6. The event bus's core module knows the names of its own dependents — fix before other modules copy the pattern

Found during architecture review: `security_base/models/security_event_bus.py`'s `_dispatch_event()` hardcodes a fixed if-chain naming five specific downstream bridge models (`security.operations.crm.bridge`, `security.fleet.ops.bridge`, etc.). This is a real architectural smell, not a stylistic nitpick — it means the *foundation* module has compile-time knowledge of modules that depend on *it*, backwards from how the dependency graph is supposed to flow, and it means every new subscriber requires editing foundation-layer code that many other modules also depend on. The risk isn't that this is hard to fix (it's a small, mechanical change — see [03-refactoring-roadmap.md](03-refactoring-roadmap.md)) — it's that if it's ported forward unexamined (easy to do, since the rest of the bus is genuinely excellent and easy to trust wholesale), every module built in Phases 1–5 that wants to subscribe to the bus will need a change to `deployfleet_core`/`deployfleet_event_bus`, which defeats much of the point of promoting the bus to foundational status in the first place. **Recommendation: fix this specific defect in Phase 0**, as part of extracting `deployfleet_event_bus`, not later.

### 4. This plan is derived from code archaeology, not from talking to a trucking company

Everything in this document set answers "what can we reuse from DeployGuard," which is the right Phase 1 question. It does not yet answer "does `customer → shipment → route → trip → delivery` actually match how a Zambian trucking company dispatches a truck." [07-domain-model-erd.md](07-domain-model-erd.md) now gives this a concrete shape — including an explicit attempt to accommodate spot loads (optional contract on a shipment), backhauls (a second trip on the same assignment chain), and consolidated cargo (many-to-many shipment↔trip) — but that document's own §3 and §6 are explicit that these are judgment calls, not validated facts. Real-world trucking dispatch may still have patterns this plan hasn't accounted for — the ERD explicitly flags owner-operator vs. company-owned trucks as an unmodeled gap, for instance. **Recommendation unchanged and now more concrete: a short, structured discovery pass with 2–3 target Zambian trucking companies (dispatcher and owner interviews, or a workflow walkthrough), using [07-domain-model-erd.md](07-domain-model-erd.md) as the thing to validate or break**, before Phase 1 schema is treated as frozen.

### 5. Rural connectivity changes the mobile app's risk profile

The source mobile app has **no offline support** — an explicit, reasonable deferral for guards posted at a fixed site with presumably stable connectivity. Long-haul trucking routes through rural Zambia are a materially different connectivity environment. If the target routes have meaningful connectivity gaps, "no offline support" stops being a Phase 4+ nice-to-have and becomes a go-live blocker for driver check-in/trip-logging. **Recommendation: confirm the connectivity profile of target routes before committing offline mobile support to Phase 4+ in the roadmap** — it may need to move earlier.

## Moderate risks

| Risk | Mitigation |
|---|---|
| Odoo edition (Community vs. Enterprise) undecided | Source explicitly punted this ("DogForce production runs Enterprise separately, cutover path undefined"). DeployFleet should decide up front — it changes what's free from the native Fleet app and what needs building. |
| GPS integration deferred, but trip/route schema decided long before it's implemented | Scope the GPS integration *contract* (what fields, what update frequency, what vendor/protocol) early even though implementation waits — avoids reworking `deployfleet_trip` later for a schema that didn't anticipate a telemetry feed. |
| ~48-module full scope is large for a first commercial release | Resolved structurally by the MVP-12 scoping in [04-module-structure.md](04-module-structure.md) and the 5-phase roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md) — confirm team size/timeline against that phase plan, and don't hesitate to push Phase 4–5 modules out of a v1 release if capacity is tight. |
| Payroll/country decoupling bug (source: `security_payroll_core` hard-depends on the Namibia pack) | Structural fix specified in [03-refactoring-roadmap.md](03-refactoring-roadmap.md) and scheduled explicitly in Phase 3 (Compliance) of the roadmap — flagged here because it's easy to silently reintroduce if whoever writes `deployfleet_payroll`'s manifest isn't aware of why it matters for the "then expand to regional logistics operators" part of the vision. |
| No CI/tests on the source's mobile controllers or newer bridge modules | Addressed structurally in Phase 0 (CI from day one) rather than left as a "we'll add tests eventually" risk. |

## Recommendations summary

1. **Resolve the Odoo edition question before writing a single model** — the vehicle-delegation pattern is already decided (see risk #2); edition is the remaining Phase 0 gate.
2. **Do not fork `security_dogforce_data` or `security_dogforce_migration` in any form.**
3. **Elevate compliance-dispatch enforcement and driver rest-hour rules to core, non-optional scope** given trucking's regulatory/safety profile — don't inherit the source's P2 prioritization for these specific items.
4. **Run a short real-world discovery pass against target Zambian trucking operators, using [07-domain-model-erd.md](07-domain-model-erd.md) as the artifact to validate or break, before freezing the Phase 1 dispatch schema** — this is the one thing no amount of source-code analysis can substitute for.
5. **Confirm target-route connectivity before deciding where offline mobile support sits in the roadmap.**
6. **Fix the event bus's hardcoded subscriber list in Phase 0**, before other modules copy the pattern by example.
7. **Treat the MVP-12 scoping in [04-module-structure.md](04-module-structure.md) as a scoping tool, not just documentation** — use it to explicitly agree what's in the first commercial release vs. later phases, matched to actual team capacity.

## Open questions for explicit sign-off before Phase 0 begins

*(The vehicle-architecture question from v1 of this document is resolved — see risk #2 — and removed from this list.)*

1. Target Odoo edition: Community only, or Enterprise features in scope?
2. Confirmed launch market details: is Zambia-only correct for v1, with Namibia truly dormant, or is there a nearer-term second country?
3. Team size/timeline — should the full 5-phase roadmap be the plan of record, or should Phase 4–5 be explicitly out of scope for a v1 release?
4. Has any discovery work already happened with real trucking operators validating [07-domain-model-erd.md](07-domain-model-erd.md), or should that be scheduled before Phase 1 schema work starts?
5. Is the owner-operator vs. company-owned-vehicle distinction ([07-domain-model-erd.md](07-domain-model-erd.md) §3) relevant to the initial target customers, or safely deferred?
