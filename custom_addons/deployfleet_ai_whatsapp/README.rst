=========================
DeployFleet AI WhatsApp
=========================

An action-capable WhatsApp channel via Meta's WhatsApp Business Cloud
API: a driver texting the word "breakdown" creates a
``deployfleet.ai.action.request`` (``pending_approval``) proposing to
mark their currently assigned vehicle broken down - see
docs/architecture/08-ai-architecture.md §5's own example, "a
WhatsApp-reported breakdown creating a real ticket."

**This module never calls ``action_approve()``.** It creates the request
and submits it for approval, full stop - a dispatcher/manager still has
to review and approve it via ``deployfleet_ai_actions`` before the
vehicle's status actually changes. A WhatsApp message can propose; it can
never execute.

Driver matching is by normalized trailing digits of ``hr.employee.mobile_phone``
against the inbound message's ``from`` number - deliberately simple, not a
full phone-number/E.164 parser. An unmatched sender or a driver with no
currently assigned vehicle gets a fallback reply and no request is
created.

**Known gap, read before going live**: the inbound webhook
(``POST /api/whatsapp/webhook``) does not verify Meta's
``X-Hub-Signature-256`` HMAC signature - anyone who discovers the URL
could currently POST a fabricated message. This is flagged explicitly,
not silently shipped as solved: verifying that signature (using the
Meta app secret, separate from the per-company access token already
configured here) is required before this endpoint should be considered
hardened against spoofed requests.
