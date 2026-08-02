# 06 — Risks and Recommendations

## Hard risks

### 1. `security_dogforce_data` must never be forked, referenced, or partially copied

This module (71,419 lines) loads a real security company's actual production data — guards, clients, contracts — from XLSX via a post-install hook. It is not "technical debt," it's a live business's operational data sitting in a codebase. It has zero architectural value to DeployFleet (it's not a reusable pattern, just a data loader pointed at specific files) and carries real risk if it ever ends up in a new commercial product's repository, even privately: it's someone else's client data, someone else's business, and not something a fork of this scope should be anywhere near. **Recommendation: exclude it explicitly and permanently — don't "review it later," don't keep a copy "for reference."** The scratch clone of the source repository used to produce this analysis should be deleted once this planning work is accepted, not kept around locally.

### 2. The `fleet.vehicle` naming collision is the single highest-leverage technical decision in this entire plan

Odoo's native Fleet app already defines `fleet.vehicle` and related models. Get the decision in [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.1 wrong — or skip it and let whoever writes `fleet_vehicle_registry` first just wing it — and the rework cascades through `fleet_fuel_management`, `fleet_inspection`, `fleet_workshop`, and every AI feature that reads vehicle data. This is why Phase 0 in [05-implementation-roadmap.md](05-implementation-roadmap.md) treats it as a blocking gate, not a "figure it out as you go" detail.

### 3. Compliance and driver rest-hour rules carry more legal weight in trucking than the source treated them

In DeployGuard, `security_compliance_roster` (document-expiry-blocks-dispatch) and rest-rule enforcement in `security_shift_planner` were real but secondary features — a guard working past their rest window is a labor-practice problem. In trucking, a driver working past a rest/hours limit, or a vehicle dispatched without valid insurance or roadworthiness, is a safety and regulatory liability with sharper legal consequences (accidents, fines, insurance voidance, license revocation). The source codebase's own `KNOWN_ISSUES.md` lists rest-rule and understaffing enforcement as "P2 — Operations completeness," i.e. nice-to-have. **Recommendation: for DeployFleet, treat hard-constraint enforcement in `fleet_compliance_dispatch` and driver rest rules in `fleet_dispatch_planner` as core, non-optional, Phase 1–3 scope — not a P2 backlog item** — regardless of how the source prioritized the equivalent feature.

### 4. This plan is derived from code archaeology, not from talking to a trucking company

Everything in this document set answers "what can we reuse from DeployGuard," which is the right Phase 1 question. It does not yet answer "does `client → contract/lane → route → trip` actually match how a Zambian trucking company dispatches a truck." Real-world trucking dispatch has patterns this plan hasn't validated against a real operator: spot loads booked ad hoc outside any standing contract, backhauls (a return trip picking up different cargo for a different customer), owner-operator trucks vs. company-owned fleet, and mixed cargo consolidation. If any of those are common in the target market, the `fleet_operations`/`fleet_dispatch` domain model in [04-module-structure.md](04-module-structure.md) needs adjustment before Phase 1 schema is frozen — and that adjustment is cheap now, expensive after Phase 1–2 are built on top of it. **Recommendation: a short, structured discovery pass with 2–3 target Zambian trucking companies (dispatcher and owner interviews, or a workflow walkthrough) before Phase 1 schema freezes**, not as a nice-to-have but as the highest-uncertainty item in this entire plan.

### 5. Rural connectivity changes the mobile app's risk profile

The source mobile app has **no offline support** — an explicit, reasonable deferral for guards posted at a fixed site with presumably stable connectivity. Long-haul trucking routes through rural Zambia are a materially different connectivity environment. If the target routes have meaningful connectivity gaps, "no offline support" stops being a Phase 4+ nice-to-have and becomes a go-live blocker for driver check-in/trip-logging. **Recommendation: confirm the connectivity profile of target routes before committing offline mobile support to Phase 4+ in the roadmap** — it may need to move earlier.

## Moderate risks

| Risk | Mitigation |
|---|---|
| Odoo edition (Community vs. Enterprise) undecided | Source explicitly punted this ("DogForce production runs Enterprise separately, cutover path undefined"). DeployFleet should decide up front — it changes what's free from the native Fleet app and what needs building. |
| GPS integration deferred, but trip/route schema decided long before it's implemented (Phase 7) | Scope the GPS integration *contract* (what fields, what update frequency, what vendor/protocol) early even though implementation waits — avoids reworking `fleet_trip_execution` later for a schema that didn't anticipate a telemetry feed. |
| 43-module scope is large for a first commercial release | The phased roadmap and install profiles in [05-implementation-roadmap.md](05-implementation-roadmap.md) exist specifically so the team isn't implicitly committed to all 43 before the first paying customer — confirm team size/timeline against the phase plan, and don't hesitate to cut Phase 5–7 modules from the first release if capacity is tight. |
| Payroll/country decoupling bug (source: `security_payroll_core` hard-depends on the Namibia pack) | Structural fix specified in [03-refactoring-roadmap.md](03-refactoring-roadmap.md) and scheduled explicitly in Phase 3 of the roadmap — flagged here because it's easy to silently reintroduce if whoever writes `fleet_payroll_core`'s manifest isn't aware of why it matters for the "then expand to regional logistics operators" part of the vision. |
| No CI/tests on the source's mobile controllers or newer bridge modules | Addressed structurally in Phase 0 (CI from day one) rather than left as a "we'll add tests eventually" risk. |

## Recommendations summary

1. **Resolve the `fleet.vehicle` naming/dependency decision and the Odoo edition before writing a single model** — Phase 0 gate, not a Phase 1 detail.
2. **Do not fork `security_dogforce_data` or `security_dogforce_migration` in any form.**
3. **Elevate compliance-dispatch enforcement and driver rest-hour rules to core, non-optional scope** given trucking's regulatory/safety profile — don't inherit the source's P2 prioritization for these specific items.
4. **Run a short real-world discovery pass against target Zambian trucking operators before freezing the Phase 1 dispatch schema** — this is the one thing no amount of source-code analysis can substitute for.
5. **Confirm target-route connectivity before deciding where offline mobile support sits in the roadmap.**
6. **Treat the install-profile structure in [04-module-structure.md](04-module-structure.md) as a scoping tool, not just documentation** — use it to explicitly agree what's in the first commercial release vs. later phases, matched to actual team capacity.

## Open questions for explicit sign-off before Phase 0 begins

1. Extend Odoo's native `fleet.vehicle` (Option 1) or build a fully standalone vehicle model (Option 2)?
2. Target Odoo edition: Community only, or Enterprise features in scope?
3. Confirmed launch market details: is Zambia-only correct for v1, with Namibia truly dormant, or is there a nearer-term second country?
4. Team size/timeline — should the full 7-phase roadmap be the plan of record, or should Phase 5–7 be explicitly out of scope for a v1 release?
5. Has any discovery work already happened with real trucking operators, or should that be scheduled before Phase 1 schema work starts?
