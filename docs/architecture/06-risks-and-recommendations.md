# 06 — Risks and Recommendations

*Revision 2 — the vehicle-architecture question (risk #2) resolved per architecture review; event-bus subscriber-coupling defect added (risk #4); [07-domain-model-erd.md](07-domain-model-erd.md) is now the concrete deliverable risk #5 was asking for. Revision 3 — renumbered for a clean sequence, two new hard risks added covering AI action safety and AI cost/data-governance. Revision 4 — all hard risks except #5 formally resolved by approved decision; this revision records the decisions as binding, not just recommended, and Phase 0 implementation proceeds against them.*

## Hard risks

### 1. `security_dogforce_data` must never be forked, referenced, or partially copied

**Status: ✅ Resolved.** `security_dogforce_data` and `security_dogforce_migration` will not exist in DeployFleet in any form — no production customer data, XLSX imports, migration scripts, or client-specific records. The DeployFleet repository contains clean demo data and synthetic trucking datasets only, with no references to DogForce operational data. Scratch clones of the source repository used for analysis are deleted after each round of review, not kept around locally.

This module (71,419 lines in the source) loads a real security company's actual production data — guards, clients, contracts — from XLSX via a post-install hook. It was never technical debt to fix; it's a live business's operational data sitting in a codebase, with zero architectural value to DeployFleet and real risk if it ever ended up in a new commercial product's repository, even privately.

### 2. The `fleet.vehicle` naming collision

**Status: ✅ Resolved.** `deployfleet.vehicle` uses Odoo's delegation inheritance:

```python
_inherits = {"fleet.vehicle": "fleet_vehicle_id"}
```

Rationale: preserves compatibility with the Odoo Fleet ecosystem, avoids duplicate vehicle records, allows DeployFleet-specific lifecycle management on top, and keeps a path open to future Enterprise compatibility. `fleet.vehicle` is the base layer; `deployfleet.vehicle` is the operational layer every other DeployFleet module references. **No module creates a standalone vehicle table, ever** — this is binding, not a style preference to reconsider per module. Full pattern: [03-refactoring-roadmap.md](03-refactoring-roadmap.md) §A.2.

### 3. Compliance and driver rest-hour rules carry more legal weight in trucking than the source treated them

**Status: ✅ Resolved.** Compliance is a core dispatch-control capability, not an optional add-on. A vehicle or driver is not dispatchable when: license expired, insurance expired, roadworthiness expired, a required certification expired, or driver rest rules are violated. Enforcement sits between trip request and dispatch approval:

```
Trip Request → Compliance Engine → Driver + Vehicle Validation → Dispatch Approval
```

Emergency overrides require an authorized role, a stated reason, a timestamp, and an audit record — no silent bypass. This is Phase 3 scope (`deployfleet_dispatch_compliance`, plus rest-rule constraints in `deployfleet_dispatch`'s scoring engine) per [05-implementation-roadmap.md](05-implementation-roadmap.md), treated as core rather than the source's "P2 — nice to have" prioritization for the equivalent guard-shift feature.

### 4. The event bus's core module knows the names of its own dependents

**Status: ✅ Resolved.** The hardcoded if-chain in the source's `_dispatch_event()` is replaced by a subscriber-registry architecture in `deployfleet_event_bus`:

```
Event Bus → Subscriber Registry → Registered Consumers
```

Modules subscribe independently, e.g. `deployfleet.event.subscribe("vehicle.breakdown.created", handler)` — the bus never has compile-time knowledge of who's listening. This removes the circular-dependency smell in the source, allows genuinely optional modules, and keeps the door open for future third-party/plugin consumers, which matters for a SaaS product's extensibility story. Implemented as part of Phase 0 — see the module itself for the concrete registry model.

### 5. This plan is derived from code archaeology, not from talking to a trucking company

**Status: 🟡 Pending validation.** The domain model in [07-domain-model-erd.md](07-domain-model-erd.md) is the architecture baseline Phase 1 builds against, but it is not yet validated against a real operator and should not be treated as frozen. Required discovery, at minimum: 2 trucking companies, 1 dispatcher interview, 1 fleet manager interview, 2 driver interviews — validating shipment lifecycle, dispatch process, route planning, billing model, vehicle ownership, driver assignment, and backhaul handling specifically. Any changes discovered should update the domain model **before** production modules depend on the parts that change. This is the one hard risk still open, and implementation of Phase 1's operational modules should not outrun it by much.

### 6. Rural connectivity changes the mobile app's risk profile

**Status: ✅ Architecture resolved** (offline support itself may still roll out in phases). DeployFleet's mobile architecture is designed for unreliable connectivity from day one rather than assuming it can be retrofitted later:

```
Mobile App → Local Database → Offline Queue → Sync Engine → Odoo API
```

Priority offline-capable workflows: driver check-in, vehicle inspection, fuel logging, breakdown reporting, document-upload queuing. The architecture must not preclude offline support even if the full implementation phases in — see [MOBILE_ARCHITECTURE.md](../../MOBILE_ARCHITECTURE.md) and [05-implementation-roadmap.md](05-implementation-roadmap.md) for where the sync engine itself lands.

### 7. AI that writes without a human approval gate is a liability, not a feature

**Status: ✅ Resolved.** AI may analyze, recommend, draft, predict, and explain, without restriction. AI may **never** directly perform a sensitive mutation. Every mutating action follows:

```
AI Suggestion → Human Review → Approval → Execution → Audit Log
```

Concretely: "your truck may require service in 500km" and "create maintenance recommendation" are allowed outputs with no gate. "Create maintenance order," "change dispatch assignment," "approve expense," and "modify payroll" all require human approval before execution — no exceptions carved out for convenience, including for AI-initiated actions sourced from WhatsApp (see [08-ai-architecture.md](08-ai-architecture.md) §8, updated to remove an earlier draft's proposed fast-tracked exception for driver-reported breakdowns — there isn't one). Every AI action stores user, model, prompt, context, recommendation, approval, and execution result — `deployfleet_ai_actions`, built to this rule from its first commit, not hardened into compliance later.

### 8. Routing business data through a third-party AI provider raises data-governance questions

**Status: ✅ Resolved.** AI usage is configurable per company and per feature, not just globally on/off. A company's AI policy shape:

```
AI Enabled: Yes
External AI Providers: Allowed
Payroll Data: Blocked
Financial Data: Blocked
Fleet Analytics: Allowed
```

Every AI module must respect data classification, user permissions, and company-level feature configuration before making a call. DeepSeek is the default **testing/development** provider; production providers remain configurable (DeepSeek, OpenAI, Claude, Gemini, and a reserved slot for future local/self-hosted models). Sensitive workflows must support disabling AI completely, disabling external AI specifically while keeping internal/private models available, or scoping per data category exactly as shown above — built into `deployfleet_ai_core`'s config model from Phase 0, not retrofitted once a customer asks.

## Moderate risks

| Risk | Mitigation |
|---|---|
| Odoo edition (Community vs. Enterprise) undecided | Still open — see open questions below. |
| GPS integration deferred, but trip/route schema decided long before it's implemented | Scope the GPS integration *contract* (what fields, what update frequency, what vendor/protocol) early even though implementation waits. |
| ~50-module full scope is large for a first commercial release | Resolved structurally by the MVP-12 scoping in [04-module-structure.md](04-module-structure.md) and the 5-phase roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md). |
| Payroll/country decoupling bug (source: `security_payroll_core` hard-depends on the Namibia pack) | Structural fix specified in [03-refactoring-roadmap.md](03-refactoring-roadmap.md), scheduled for Phase 3. |
| No CI/tests on the source's mobile controllers or newer bridge modules | Addressed structurally: CI and a test-from-first-commit bar are part of Phase 0 scaffolding. |
| AI token/cost budget has no default value yet | Still open — the per-company policy shape is resolved (risk #8), but the specific default numbers for the MVP release are not yet set. |

## Recommendations summary

1. **Resolve the Odoo edition question** — the last unresolved Phase 0 gate; every other hard risk is now decided.
2. ~~Do not fork `security_dogforce_data` or `security_dogforce_migration` in any form.~~ — done; see risk #1.
3. ~~Elevate compliance-dispatch enforcement and driver rest-hour rules to core, non-optional scope.~~ — done; see risk #3.
4. ~~Fix the event bus's hardcoded subscriber list.~~ — done; see risk #4.
5. **Run a short real-world discovery pass against target Zambian trucking operators, using [07-domain-model-erd.md](07-domain-model-erd.md) as the artifact to validate or break** — the one hard risk still genuinely open. Do not let Phase 1 implementation get far ahead of this.
6. ~~Confirm target-route connectivity before deciding where offline mobile support sits in the roadmap.~~ — architecture resolved regardless of the answer; see risk #6.
7. ~~Never ship an AI-initiated write without the human-approval gate.~~ — done, and binding; see risk #7.
8. ~~Confirm data-governance expectations and build the per-feature AI provider opt-out as day-one capability.~~ — done; see risk #8.
9. **Treat the MVP-12 scoping in [04-module-structure.md](04-module-structure.md) as a scoping tool, not just documentation** — still applies as Phase 0–5 implementation proceeds.

## Open questions still requiring sign-off

*(Risks #1–4 and #6–8 are resolved with binding decisions recorded above. Risk #5's discovery work is scheduled, not yet done, and should not be treated as "closed enough to ignore" just because implementation has started.)*

1. Target Odoo edition: Community only, or Enterprise features in scope?
2. Confirmed launch market details: is Zambia-only correct for v1, with Namibia truly dormant, or is there a nearer-term second country?
3. Team size/timeline — should the full 5-phase roadmap be the plan of record, or should Phase 4–5 be explicitly out of scope for a v1 release?
4. Has the real-world discovery work for risk #5 been scheduled yet? It has not started as of Phase 0 implementation beginning — flagged so it doesn't get silently dropped now that most other risks are closed.
5. What are the actual default AI token/cost budget numbers for the MVP release, and who gets alerted when a company approaches its limit?
