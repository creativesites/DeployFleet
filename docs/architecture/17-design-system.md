# 17 — Design System

**Status:** Specification, not code. This document is what a future `deployfleet_ui` design-system module's tokens should encode — colors, spacing, typography, elevation, glass, iconography, motion timing, AI styling, dark mode, and accessibility rules — specified precisely enough that building the actual SCSS/CSS-custom-property file is a transcription exercise, not a design exercise. Sibling to [16-experience-architecture.md](16-experience-architecture.md) (the why/what/in-what-order) and [18-component-library.md](18-component-library.md) (the component catalog that consumes these tokens) and [19-animation-guidelines.md](19-animation-guidelines.md) (the motion timing detail summarized in §7 below).

**The goal, stated once so every rule below can be checked against it:** DeployFleet's equivalent of Android's Material Design or iOS's Human Interface Guidelines — a single reference so complete that no developer, on any module, ever needs to invent a button color, a shadow value, or a spacing decision from scratch. Every visual decision in [16-experience-architecture.md](16-experience-architecture.md) §7 traces back to a rule in this document; where it doesn't yet, that's a gap in this document to close, not a license to improvise per-screen.

**Why this exists as its own document, not a section of doc 16:** doc 16 §3.0 diagnosed DeployGuard's central process failure precisely — a real design-system file existed (`security_base/static/src/css/design_system.css`) but nothing after it consumed it, so a dozen dashboards each reinvented the same near-identical navy/slate palette under a different two-letter prefix. A design system that lives buried as one section of a strategy document is exactly as easy to skip as DeployGuard's was. Giving it its own numbered, linkable document makes "did you check the design system" an unambiguous, single-answer question during code review.

---

## 1. Visual personality — the brief this token system executes

Per [16-experience-architecture.md](16-experience-architecture.md) §2.1: **Tesla Fleet, Stripe, Linear, Notion, Uber Freight, Motive, Samsara** — modern, fast, minimal, confident — not DeployGuard's dark, dense, military-operations-center register. Every token below is chosen against that brief. Where a DeployGuard value is reused (a shadow recipe, a blur amount), it's reused because it's genuinely well executed, restyled in DeployFleet's own palette, never carried over as-is.

---

## 2. Color system

### 2.1 Brand palette

Deliberately distinct from DeployGuard's Goldman-Sachs-adjacent deep navy (`#1B3A6B` family) — DeployFleet earns its own identity rather than reading as a reskin, per [CLAUDE.md](../../CLAUDE.md)'s explicit instruction.

| Role | Direction | Rationale |
|---|---|---|
| **Primary** | Deep teal-blue (a cooler, more saturated blue-green than DeployGuard's navy — think horizon-at-dusk, not pinstripe-suit) | Professional and enterprise-credible without borrowing DeployGuard's specific hue; evokes movement, sky, and distance rather than finance |
| **Accent** | Warm amber-orange, drawn from road-safety/high-visibility signage | The one color that earns attention — reserved for primary CTAs, the AI-adjacent accent in the Copilot Rail's chrome (not its content, which is violet — see §2.3), and the Launcher's priority-workspace strip. Never used decoratively; if it's on screen, it's asking for a click. |
| **Neutral scale** | Slate/graphite grays, cooler than DeployGuard's warmer slate | Workspace Layer surfaces, body text, borders — the majority of any screen's actual pixels |

### 2.2 Status semantics — the platform-wide rule

Reused directly from doc 16 §4, restated here as the canonical source (doc 16 should be read as summarizing this table, not the other way around):

| Meaning | Color family | Applies to | Business-meaning override |
|---|---|---|---|
| On-time / compliant / available / healthy | Green | Trip on schedule, document valid, vehicle available, driver compliant | — |
| Needs attention soon / approaching threshold | Amber | Document expiring within N days, maintenance due soon, invoice approaching due date | — |
| Critical / blocking / expired / broken | Red | Expired compliance document, vehicle breakdown, overdue invoice, hard-disqualified dispatch candidate | — |
| Informational / in progress / neutral state | Blue | In-transit, draft, awaiting confirmation | — |
| **AI-authored or AI-suggested content** | **Violet** | Any AI-agent suggestion, prediction, or pre-filled field, anywhere in the product, before human approval | — |

**The business-meaning-override rule** (doc 16 Principle 4): color follows what the number *means*, not which direction it moved. A rising payroll/fuel/maintenance cost is red, a falling one is green, even though naively "up" might default to a warning triangle and "green means go up" is the more common (wrong, for cost metrics) instinct. Every KPI in doc 18's `MetricCard`/trend-arrow implementation must have its color direction decided explicitly, per-metric, at build time — never inherited from a shared "positive = green" default.

### 2.3 The AI-content violet convention, specified precisely

The single most important net-new color decision relative to DeployGuard (whose AI engine never had a UI to need one). Rules:

- Any card, badge, field, or panel showing AI-generated or AI-suggested content carries a **violet left-border stripe** (on cards/rows) or a **violet badge with a small distinct icon** (inline, e.g., next to a pre-filled field) — never just italicized text or a tooltip, which a user can miss.
- Violet is **reserved exclusively** for this purpose. It must not appear anywhere else in the palette (not as a fifth "neutral" accent, not as a decorative gradient stop) — its entire value is that seeing violet means "a model produced this, a human hasn't acted on it yet."
- Once a human accepts an AI suggestion, the violet treatment is removed and the resulting record displays with normal status colors — violet marks *pending, unreviewed* AI output specifically, not "AI was involved historically."

### 2.4 Dark mode

**Decision: supported, not deferred.** Twenty-four-hour dispatch operations are a real operating pattern for trucking companies, and a night-shift dispatcher staring at a bright white Workspace Layer for eight hours is a genuine usability failure, not a nice-to-have. Rules:

- Every token in this document is defined as a light/dark pair, not a single value with a dark-mode override bolted on later.
- **Command Layer** surfaces already lean dark by design (§4) — dark mode mostly changes the Workspace Layer, which flips from near-white to a deep, desaturated slate (not pure black, which crushes shadow/elevation legibility).
- Status colors (§2.2) shift luminance, not hue, between modes — green stays green, just a lighter/brighter value against a dark background, preserving the color language's consistency across mode.
- The AI-violet convention (§2.3) is the one color explicitly checked for sufficient contrast in both modes, since it's the color this whole system depends on being unmissable.

---

## 3. Typography

- **One type scale, shared by both layers.** Command Layer permits larger display numbers for KPI/hero moments (Mission Control's revenue figure, the Fleet Score); Workspace Layer stays disciplined at body/label sizes suited to dense scanning.
- **One typeface family, platform-wide** — a single modern, highly legible sans-serif (not DeployGuard's mixed usage), chosen for numeral legibility specifically, since so much of this product's content is numbers read at a glance (KPIs, scores, currency) rather than prose.
- **Numerals get their own discipline**: tabular figures wherever numbers appear in a column (billing tables, fuel logs) so digits align vertically — a small, easy-to-skip detail that materially affects how "considered" a dense financial table feels.

---

## 4. Spacing & layout grid

- **8px base unit**, all spacing values multiples of it (8/16/24/32/48/64) — matches DeployGuard's own implicit convention (visible across its dashboards' padding values) and is a safe, well-trodden default.
- **A consistent content-width ceiling** on Workspace Layer screens so dense tables don't stretch to unreadable line lengths on wide monitors — Command Layer overlays (Launcher, Mega Menus) already cap at ~1100–1180px per DeployGuard's own precedent (§3.1/§3.3 of doc 16), kept as the ceiling for DeployFleet's equivalents too.

---

## 5. Elevation, shadow & border radius

- **Elevation is reserved for genuine state, not applied decoratively to every panel.** A resting card, a hovering card, and an open modal are three distinct elevation steps; a screen where every panel already has a heavy shadow has nothing left to communicate when something actually needs to draw attention.
- **Border radius**: one consistent scale — a tighter radius for dense Workspace Layer cards/rows (reads as precise, professional), a more generous radius for Command Layer surfaces (reads as approachable, matches the Launcher/Mega Menu's already-generous ~20px precedent from DeployGuard, kept because it's genuinely well judged).
- **Shadows are colored, not pure black-alpha** — a very subtle tint of the primary teal-blue in shadow color (a common technique in modern SaaS product design, part of why Stripe/Linear-class products feel considered rather than default) rather than generic `rgba(0,0,0,.1)` shadows.

---

## 6. Glassmorphism / glass effects — codified per layer

Directly reused from doc 16 Principle 1, specified here with the actual recipe:

- **Command Layer glass recipe (revised — light panel, not dark):** a dimming scrim (`rgba` of a near-black, ~0.45 opacity — dims the page behind the panel, independent of the panel's own color) + heavy blur (24–28px) + a slight saturation boost on whatever's behind it, behind a **light, near-white translucent panel** (`--df-glass-panel-bg`, ~0.92 opacity) with a hairline border and dark text. **Changelog note:** this supersedes the original recipe below, kept for the record — the Enterprise OS Launcher's actual recipe (doc 16 §3.2), a dark translucent gradient card with light text, inherited from DeployGuard because it was genuinely well executed. Phase C implementation shipped that dark recipe across the Launcher, Mega Menus, Mission Control, and the Copilot Rail; mid-Phase-D, an explicit product decision ("only light backgrounds, as much as possible") retrofitted all four to the light recipe above, given the same weight as any other implementation-discovered correction in this document. The dark recipe's *structure* (scrim + blur + saturation + translucent card + hairline border) is unchanged — only the panel's luminance and text color flipped. Every token needed for either recipe already exists in `tokens.scss` (`--df-glass-panel-bg` and `--df-glass-border` are theme-aware and flip automatically between the light and dark recipe per `prefers-color-scheme`/`data-theme`, exactly the way the rest of the neutral scale already does).
- **Workspace Layer: no blur, ever.** Flat, near-white (or dark-mode slate) surfaces, shadow reserved for true elevation changes per §5. This is deliberately the opposite instinct from Command Layer surfaces, and getting the two confused (blur behind a dense list or billing table) is called out explicitly in doc 16 as the single most common way "premium" tips into "annoying."
- **Performance guardrail**: `backdrop-filter` is expensive on low-end Android hardware common in the target market. Command Layer glass is fine on desktop/tablet dispatcher and manager surfaces; any driver-facing mobile screen defaults to the flat Workspace Layer treatment even where the rest of the platform uses glass, full stop, regardless of which layer the screen would otherwise belong to.

---

## 7. Motion — summary; full spec in doc 19

Two rules stated here because they're design-system-level constraints, not just animation-catalog entries (full timing table lives in [19-animation-guidelines.md](19-animation-guidelines.md)):

- **Motion communicates state change, never ambient decoration.** A card entering, a status flipping, a value updating — never a continuously pulsing background or a decorative particle effect that runs regardless of what the user is doing. This is part of what separates DeployFleet's target register (§1) from anything that reads as "trying to look futuristic."
- **Durations stay in the 100–300ms range** across the whole product (exact per-interaction values in doc 19) — a working dispatcher should never wait on an animation to finish before the next action is available.

---

## 8. Iconography

- **One icon set, used consistently across the entire product** — DeployGuard visibly mixed icon libraries across modules (a small but real inconsistency); DeployFleet picks one and never introduces a second.
- **Icons carry meaning, not decoration** — every icon used in a status badge, a nav tile, or a KPI card header should be resolvable to a specific, memorizable meaning (a fuel icon always means fuel-related, never repurposed for something unrelated elsewhere in the product).

---

## 9. Loading states

- **Skeleton loaders, not spinners, wherever the eventual content's shape is already known** (a list about to populate, a card about to fill in) — a spinner is only appropriate when the shape of the incoming content is genuinely unknown.
- **Shimmer animation** on skeletons follows the same motion-discipline rule (§7/doc 19): communicates "loading," stops the instant content arrives, never lingers for effect.

---

## 10. AI styling — summary; see doc 16 §8 for the ambient strategy

- The violet convention (§2.3) is this document's contribution; doc 16 §8 specifies *where* and *how* it appears platform-wide (the AI Recommendation Card pattern, the Copilot Rail, the Copilot Console).
- Every AI-authored value in a form field (a pre-filled suggestion, not yet accepted) gets the same violet left-border treatment as a full card — consistency at the field level matters as much as at the card level, since a user should never have to learn two different "this came from AI" visual languages depending on where in the UI they encounter it.

---

## 11. Accessibility

- **WCAG AA contrast minimum, checked explicitly for Command Layer glass surfaces** in both light and dark ambient conditions (§6's performance guardrail exists for cost; this rule exists for legibility — a translucent card that tests well in a design tool and poorly in truck-stop sunlight has failed).
- **Reduced-motion equivalents required for every animation** without exception (§7/doc 19) — no component ships without one.
- **Touch targets sized for gloved, one-handed, sunlit mobile use** on any driver-facing screen — larger than a desk-bound desktop/tablet target, a direct consequence of doc 16 Principle 6 (truck-stop-first, not phone-mockup-first).
- **Keyboard navigation is a first-class requirement for the Command Palette and Launcher specifically** (§5 of doc 16) — these are explicitly designed as keyboard-first power-user tools (`Cmd/Ctrl+K`, `Alt+<letter>`), so keyboard support there isn't an accessibility afterthought, it's the primary interaction model.

---

## 12. Component rules — the contract every component in doc 18 must satisfy

- **Every interactive component supports, at minimum**: default, hover, active/pressed, focus (keyboard-visible), disabled, loading, and empty states. A component shipped without an explicit empty state is a component that will eventually show broken-looking blank space in production.
- **No module hand-rolls a button, card, badge, or modal.** If a screen needs a visual element not yet in doc 18's catalog, the correct action is to add it to doc 18 (extending the shared library), not to write bespoke CSS scoped to one module — the exact discipline DeployGuard's team visibly intended (§0/doc 16 §3.0) and didn't enforce.
- **Every component consumes this document's tokens by reference, never by literal value.** A component's SCSS/JS should never contain a literal hex code, pixel value, or duration — only a reference to a design-system token. This is the mechanical guarantee that keeps doc 17 authoritative rather than aspirational.

---

## 13. Governance

This document is the token-level authority beneath [16-experience-architecture.md](16-experience-architecture.md); [18-component-library.md](18-component-library.md)'s components and [19-animation-guidelines.md](19-animation-guidelines.md)'s timing values must not contradict it. Any new color, spacing value, or visual treatment proposed anywhere in the product gets added here first — the same "update the doc in the same session" discipline [CLAUDE.md](../../CLAUDE.md) §8 already requires of every other architecture document.
