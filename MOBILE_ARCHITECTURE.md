# Mobile Architecture

Mobile is a first-class product surface for DeployFleet, not an afterthought bolted onto the Odoo backend — the primary users (drivers, dispatchers, fleet managers/supervisors) work from phones and tablets in the field, not from a desk. Full reuse analysis: [docs/architecture/02-reuse-strategy.md](docs/architecture/02-reuse-strategy.md) §6. Module list: [docs/architecture/04-module-structure.md](docs/architecture/04-module-structure.md).

## Three apps, not one

DeployGuard shipped one mobile app with three role-routed sections (supervisor/manager/owner). DeployFleet splits by role instead, because drivers, dispatchers, and customers have different enough usage patterns to warrant it:

| App | Backend module | Primary users | Core workflows |
|---|---|---|---|
| **Driver** | `deployfleet_mobile_driver` | Drivers | Assigned trips, navigation, pre/post-trip inspections, proof-of-delivery capture (signature, photo, GPS stamp), breakdown reporting, compliance document access, dispatcher communication |
| **Dispatcher** | `deployfleet_mobile_dispatcher` | Dispatchers, fleet managers | Live operations view, trip monitoring, alerts, overtime/exception approvals |
| **Customer** | `deployfleet_mobile_customer` | Shippers/customers | Shipment tracking, delivery status, document access |

Whether these ship as three separate app binaries or three route groups within one shell sharing a common core is an implementation-time decision, not an architecture-time one — the layers below are shared regardless of that packaging choice.

## Shared technical foundation (reused from DeployGuard, largely as-is)

- **Expo Router**, file-based routing with role route-groups (`(auth)`, `(driver)`, `(dispatcher)`, `(customer)`).
- **`src/api/client.ts`** — Axios instance with session-cookie/header injection and auth-expiry handling. No domain coupling; reused verbatim.
- **`src/api/auth.ts`** — login/logout via Odoo's standard `/web/session/authenticate`. **Fix during the port, don't carry forward**: the source infers role from a username/name heuristic instead of actual Odoo groups — fetch real groups via a `/me`-style endpoint from day one.
- **`src/stores/`** — Zustand for session/UI state (current user, selected date/site, refresh triggers). No domain coupling.
- **`src/theme/`** — design tokens, restyled per DeployFleet's glassmorphic design language (see [CLAUDE.md](CLAUDE.md) §5) rather than DeployGuard's dark theme, but the token-based approach itself is reused.
- **`src/components/`** — generic atoms (`KpiMetric`, `StatusBadge`, a check-in/action button) reuse verbatim; domain-shaped components (`GuardCard`, `SiteKpiCard`) are rebuilt as `DriverCard`, `VehicleCard`, `ShipmentCard`, `RouteKpiCard` following the same component contract.

## Backend API contract (reused pattern, rewritten endpoints)

Every mobile endpoint is a thin REST JSON controller over the Odoo ORM — no business logic duplicated in the mobile app:

- Session-cookie auth via standard Odoo JSON-RPC — unchanged.
- `@require_group()`-style decorator gating every endpoint by Odoo security group — unchanged pattern, re-pointed at `group_deployfleet_driver`/`_dispatcher`/`_manager`/`_owner`.
- Response envelope `{ "success": true, "data": {...} }` / `{ "success": false, "error": "..." }` — unchanged.
- Endpoint *queries* are a full rewrite against the new trip/shipment/dispatch schema in [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — the source's attendance/roster queries don't apply. **Do not port forward the source's documented field-name bugs** (e.g. a controller querying a field name that doesn't match the model) — this is a known defect class in the DeployGuard mobile controllers; write a controller-level test per new endpoint as it's built, not after.

## Push notifications

Wired end-to-end from the start, unlike the source (where an Expo device-token field exists but nothing sends to it). `deployfleet_mobile_push_bridge` subscribes to `deployfleet_event_bus` and turns operational events (dispatch assigned, trip delayed, vehicle breakdown, compliance bypass) into push notifications to the right role — this is more time-critical for a dispatcher than the equivalent was for security operations, so don't defer it the way the source did.

## Offline support — a genuinely open risk, not a settled deferral

The source mobile app has no offline queue at all, deferred as reasonable for guards posted at a fixed site with presumably stable connectivity. Long-haul trucking routes through rural Zambia are a materially different connectivity environment. **Confirm the connectivity profile of target routes before assuming offline support can wait until a late phase** — see [docs/architecture/06-risks-and-recommendations.md](docs/architecture/06-risks-and-recommendations.md) risk #6. If confirmed as a real gap, this moves earlier in [docs/architecture/05-implementation-roadmap.md](docs/architecture/05-implementation-roadmap.md), not treated as a fixed Phase 4+ item regardless of what the connectivity data says.

## Design language

Mobile UI follows the same modern glassmorphic, enterprise-clean aesthetic as the web client (see [CLAUDE.md](CLAUDE.md) §5) — not default native-component styling, and not a re-skin of DeployGuard's dark theme. Component design should prioritize clarity for a driver glancing at a phone mid-trip over density or information-per-screen.
