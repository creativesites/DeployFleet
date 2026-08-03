# 19 — Animation Guidelines

**Status:** Specification, not code. Exact timing, easing, and per-interaction motion rules, precise enough that two different developers building two different components produce animations that feel like the same product. Sibling to [16-experience-architecture.md](16-experience-architecture.md) (why motion matters and where), [17-design-system.md](17-design-system.md) (§7's summary rules this document details in full), and [18-component-library.md](18-component-library.md) (the components these timings apply to).

**The governing rule, stated once so every timing value below can be checked against it:** motion communicates *state change*, never *atmosphere*. A card entering, a status flipping, a value updating, a drag-and-drop completing — never a continuously pulsing background, a decorative particle effect, or an animation that runs regardless of what the user just did. This is the mechanical difference between DeployFleet's target register ([16-experience-architecture.md](16-experience-architecture.md) §2.1: Tesla Fleet, Stripe, Linear, Notion) and anything that reads as "trying to look futuristic."

---

## 1. Timing scale

Four duration bands, used consistently rather than each developer picking a number that "feels right":

| Band | Duration | Used for |
|---|---|---|
| **Micro** | 100–120ms | Button press/hover feedback — anything that responds directly to a pointer already in motion |
| **Standard** | 150–220ms | Card lifts, panel transitions, badge/status color changes — the majority of this document's entries |
| **Entrance** | 220–300ms | Modals, drawers, the Launcher/Mega Menu overlay appearing — bigger surfaces earn slightly longer, still fast, entrances |
| **Ambient (rare, deliberate only)** | 1.5–2.5s cycle | The one class of exception: a slow, restrained pulse marking something that genuinely needs sustained attention (an unresolved critical urgency indicator) — never used for anything else, and always stoppable on hover/focus |

**No animation in this product should ever exceed ~300ms for a one-shot transition.** A working dispatcher should never wait on an animation to finish before the next action is available — this is doc 17 §7's rule, restated here as a hard ceiling, not a suggestion.

**Easing**: a single consistent "ease-out, slight overshoot-free" curve for entrances (matching DeployGuard's own well-executed mega-menu entrance curve, restyled, not its literal values) and a plain ease-in-out for micro-interactions (hover, press). One curve family, used everywhere, is what makes motion read as *a language* rather than *five different developers' five different guesses* — exactly the inconsistency doc 16 §3.0 found across DeployGuard's own dashboards.

---

## 2. Per-interaction motion spec

| Interaction | Motion | Duration band |
|---|---|---|
| **Card hover/lift** | Subtle upward translate + shadow deepening (per [17-design-system.md](17-design-system.md) §5's elevation steps) | Standard, ~180ms |
| **Button press** | Slight scale-down (never full opacity change alone — a scale reads as "pressed" more clearly) | Micro, ~120ms |
| **Hover (general)** | Scale 1.02, never larger — a bigger scale reads as jarring on dense screens | Micro |
| **Dialog/modal entrance** | Scale-and-fade in from ~0.98 to 1.0, backdrop fading in simultaneously | Entrance, ~220ms |
| **Drawer/bottom-sheet entrance** | Slide in from the relevant edge, with the drag-handle (mobile) visible immediately, not faded in separately | Entrance, ~250ms |
| **AI content appearing** (an AI Recommendation Card, an AI Badge on a field) | A single gentle pulse on arrival — once, not continuous — drawing the eye without becoming ambient decoration | Standard, one cycle only |
| **Success confirmation** | A brief green "sweep" or checkmark-draw across the affected element, not just a toast appearing elsewhere on screen | Standard, ~200ms |
| **Error/validation failure** | A small shake (2–3 cycles, low amplitude) on the offending field/button, paired with the error message appearing **instantly**, not eased in — per §3 below, a user waiting on an answer should never wait on an animation | Micro-scale shake, but the message itself is not animated in |
| **Loading (shape known)** | Shimmer sweep across a Skeleton Loader (doc 18 §2/§3), looping only while genuinely loading, stopping the instant content arrives | Continuous while loading, but this is the one legitimate continuous-motion case since it directly represents an ongoing state, not decoration |
| **Loading (shape unknown)** | A plain spinner, used only when a skeleton genuinely can't be shaped in advance | Continuous while loading |
| **Drag-and-drop pickup** (Dispatch Board, per [16-experience-architecture.md](16-experience-architecture.md) §7.9) | A slight lift + subtle rotation on pickup, snapping cleanly (no bounce/overshoot) into place on drop | Micro on pickup, instant snap on drop |
| **Critical urgency pulse** (an unassigned shipment approaching its pickup window, per doc 16 §3.6/§7.9) | The one deliberate Ambient-band exception — a slow box-shadow pulse, stopping on hover/focus so it never fights active interaction | Ambient, 1.5–2.5s cycle |
| **Map pin/breadcrumb updates** (Live Fleet Map) | A new breadcrumb point fades in; a pin never "jumps" instantly across the map without at least a brief eased transition, which would read as a glitch rather than movement | Standard |
| **Value/KPI number updates** (a `MetricCard`'s number changing on refresh) | A brief count-up/count-down transition between old and new value, not an instant swap, so a user's eye can register that something changed and in which direction | Standard, ~200ms |
| **Status color transitions** (a badge flipping from amber to red as a document expires) | A smooth color cross-fade, not an instant hard swap | Standard |

---

## 3. What never animates

- **Data tables re-sorting or re-filtering** — instant. A user waiting on a filtered result should get it immediately, not watch rows re-flow decoratively.
- **Critical alerts appearing** — instant, full stop. An "expired compliance document" or "vehicle breakdown" notice is not the place for a tasteful fade-in; it should be on screen the moment it's true.
- **Form validation errors** — the message itself appears instantly (only the field's shake, per §2, is animated) — a user who just submitted a form is waiting for an answer, not for a transition to resolve.
- **Anything on a driver-facing mobile screen under real connectivity/performance constraints** ([16-experience-architecture.md](16-experience-architecture.md) §2.6 Principle 6, [17-design-system.md](17-design-system.md) §6's performance guardrail) — when in doubt on a low-end Android device, cut the animation, don't degrade it.

---

## 4. Reduced motion & performance

- **Every animation in §2 has a static equivalent**, activated by the user's OS-level reduced-motion preference — no exceptions, including the Ambient-band critical-urgency pulse (which becomes a static, still-attention-grabbing color/border treatment instead).
- **`backdrop-filter`-based entrances (Command Layer glass, per doc 17 §6) are the first thing to simplify on low-end hardware** — a plain, fast fade is an acceptable degraded fallback; a frozen or stuttering blur is not acceptable under any circumstance.
- **Animation is never a substitute for actual data freshness.** A pulsing "LIVE" label on data that's actually load-on-open (DeployGuard's own cosmetic mistake, flagged directly in doc 16 §3.7/§7.10) is a false promise this document's motion language must never make — if a surface's data isn't actually live, don't animate it as if it is.

---

## 5. Governance

This document's timings must not contradict [17-design-system.md](17-design-system.md) §7's summary rules — if the two ever disagree, doc 17 is the constraint and this document is the detail that must fit inside it. Any new animated interaction proposed anywhere in the product gets a row added to §2's table before it ships, not after — the same "update the doc in the same session" discipline [CLAUDE.md](../../CLAUDE.md) §8 already requires of every other architecture document.
