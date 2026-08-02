# 10 — Lead Intelligence Architecture (long-term vision, not current MVP scope)

**Status: vision, not committed scope.** This document captures a proposed product direction — AI-powered lead capture, qualification, and sales automation for trucking companies, freight brokers, and dispatch companies — for the record and for future planning. Per explicit instruction when this was proposed: the MVP stays focused on fleet foundation, drivers, trips, dispatch board, maintenance, billing, and AI core (the modules already built or scoped in [04-module-structure.md](04-module-structure.md) and [05-implementation-roadmap.md](05-implementation-roadmap.md)). Nothing in this document should be implemented before those are proven with a real customer — see the sequencing note in §6.

## 1. Purpose

Turn every incoming inquiry — WhatsApp message, email, website form, referral, phone call — into a qualified freight opportunity, for the commercial roles this product doesn't yet serve: trucking companies looking for customers, freight brokers, third-party dispatch companies, transport agents. This is a genuinely different user (sales/ops management chasing business) from the operational users (drivers, dispatchers, fleet managers) the current MVP targets.

## 2. Proposed modules

| Module | Purpose |
|---|---|
| `deployfleet_lead_capture` | Multi-channel lead ingestion (website form, WhatsApp Business, email, phone log, manual entry, CSV import, customer portal request) and basic CRM integration (Odoo's `crm` app, the same pattern `deployfleet_operations_crm`/`deployfleet_billing_crm` already use elsewhere in this product) |
| `deployfleet_lead_ai` | AI extraction (turn free-text/voice into structured cargo/route/frequency/urgency fields), AI lead scoring, next-best-action recommendations |
| `deployfleet_sales_automation` | Follow-up sequencing, reminders, "no response in N days" triggers |
| `deployfleet_whatsapp_sales` | WhatsApp-based sales assistant — extends the existing `deployfleet_ai_whatsapp` bridge rather than duplicating a second WhatsApp integration |
| `deployfleet_customer_intelligence` | Customer history, behavior, profitability — a natural extension of the Finance Agent already catalogued in [08-ai-architecture.md](08-ai-architecture.md) §6 |

## 3. Illustrative capability, not a spec

The following examples describe the *shape* of the intended behavior, not a committed feature list or field schema — that design work happens if and when this becomes real scope.

- **AI extraction**: an inbound message like "Need 30 tonnes of fertilizer moved from Dar es Salaam to Lusaka before month end" becomes a structured opportunity (cargo, weight, route, deadline, recommended vehicle type, priority) instead of a human re-typing it into a form.
- **AI scoring**: every lead gets a score with stated reasons (repeat route, existing relationship, payment history) and stated risks (no credit history, aggressive deadline) — not a black-box number.
- **Follow-up automation**: "no response from Customer X in 5 days" surfaces a suggested action with a drafted message, for a human to approve and send — not an auto-sent message. This is not optional framing; it follows directly from §5 below.
- **Sales assistant**: a user can ask "which leads should I prioritize today?" and get a ranked list with estimated value — the same "Ask AI" interaction pattern already specified in [08-ai-architecture.md](08-ai-architecture.md) §4, not a new UI paradigm.

## 4. This is not a new AI architecture — it's two new agents in the existing one

Per [08-ai-architecture.md](08-ai-architecture.md) §6, agents are configuration inside `deployfleet_ai_agents` (system prompt, allowed actions, data scope), not separate modules. A **Sales Agent** slots into that same catalog:

| Agent | Capabilities | Requires human approval for |
|---|---|---|
| Sales Agent | Analyze leads, draft responses, qualify customers, predict revenue | Creating a contract, sending a quote — no AI-drafted commercial commitment goes out without a human confirming it, same rule as every other agent in [08-ai-architecture.md](08-ai-architecture.md) §5 |

No new provider router, no new cache/usage/budget infrastructure, no new permission model — `deployfleet_ai_core`, `deployfleet_ai_permissions`, and `deployfleet_ai_actions` (once built) serve this agent exactly as they serve Fleet Analyst, Dispatch, Maintenance, Finance, Compliance, and Customer. The only genuinely new engineering is the lead-capture/extraction pipeline (§2) and the sales-specific agent configuration — not new AI plumbing.

## 5. The approval rule is not optional here either

[06-risks-and-recommendations.md](06-risks-and-recommendations.md) risk #7 — no AI-initiated write without a human approval gate — applies with at least as much force to sales as to dispatch or maintenance. An AI that can autonomously send a quote, commit to a rate, or promise capacity is making a financial commitment on the company's behalf. Every mutating sales action (send message, create contract, issue quote) routes through `deployfleet_ai_actions` exactly like a dispatch or maintenance action would. There is no "sales is lower stakes so it gets an exception" carve-out — if anything, an autonomously-sent commercial commitment is a sharper liability than an autonomously-created maintenance reminder.

## 6. Sequencing — explicitly not before the MVP proves out

This is new commercial surface area (sales/CRM users), not an extension of the operational core the current MVP targets. Recommended sequencing:

1. Prove out Phases 1–5 from [05-implementation-roadmap.md](05-implementation-roadmap.md) with the real customer already onboarding.
2. Only then evaluate whether lead intelligence is the next investment, versus deepening the operational product (workshop, compliance, full mobile apps) that a trucking company running the system day-to-day needs first.
3. If pursued, `deployfleet_lead_capture` (the non-AI CRM integration) should land before `deployfleet_lead_ai` — same pattern as [08-ai-architecture.md](08-ai-architecture.md) §11's "foundation before features" sequencing, and the extraction/scoring features need real lead volume to be worth building against, the same reasoning that pushed AI features in the operational roadmap to follow real trip/fuel data rather than precede it.

This module group is not numbered into the 5-phase roadmap in [05-implementation-roadmap.md](05-implementation-roadmap.md) — it's tracked here as a candidate Phase 6+, to be scheduled explicitly if and when the business decides to pursue it, not implied by its presence in this document.
