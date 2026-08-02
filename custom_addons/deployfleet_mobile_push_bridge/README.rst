=================================
DeployFleet Mobile Push Bridge
=================================

Closes the "FCM/Expo push not wired (device-token field exists, unused)"
gap flagged in docs/architecture/02-reuse-strategy.md §6.

``deployfleet.mobile.device`` registers a push token (Expo token format)
per logged-in user, from any of the three mobile apps, via a single
shared ``/api/mobile/push/register`` endpoint. ``ir.rule`` restricts
every user (internal or portal) to their own device rows.

``deployfleet.mobile.push.bridge`` subscribes generically to
``deployfleet.*`` on the event bus and matches against a small fixed
table of push-worthy events (trip delayed, delivery completed, dispatch
assigned, vehicle breakdown) - deliberately a fixed table rather than a
data-driven rule model like ``deployfleet_notifications``, since this
module's whole job is to keep the Expo HTTP dependency scoped to exactly
this bridge, not spread across a generic rule engine.

A failed push is logged and swallowed, never raised - a broken device
token must never break event dispatch for every other subscriber.
