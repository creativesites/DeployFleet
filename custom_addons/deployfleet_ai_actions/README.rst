========================
DeployFleet AI Actions
========================

The mandatory suggestion -> permission check -> human approval -> execute
-> audit pipeline for any AI-initiated write, per
docs/architecture/08-ai-architecture.md §5 - a hard constraint per that
document, and CLAUDE.md §4 / hard risk #7: **there is no auto-execute
path in v1, full stop.**

``deployfleet.ai.action.request`` moves through
``draft -> pending_approval -> approved/rejected -> executed/failed``.
The only way to reach ``executed`` is ``action_approve()``, which:

- refuses to run unless the request is currently ``pending_approval``;
- refuses to run unless the approving user holds
  ``deployfleet_security.group_deployfleet_manager`` or above - checked in
  Python, not just via the button's view-level ``groups`` attribute (a
  view restriction is a UI convenience, not a security boundary);
- is the *only* caller of ``_execute()`` anywhere in this module - no
  cron, no server action, no other code path reaches it.

``_execute()`` writes via the normal ORM as the approver, never
``sudo()`` - an AI-proposed action is subject to exactly the same access
rights and field validation a human entering the same data by hand would
be. A small denylist (``_FORBIDDEN_TARGET_MODELS`` in
``models/deployfleet_ai_action_request.py``) blocks auth/security/system
models (``res.users``, ``res.groups``, ``ir.rule``, ``ir.model.access``,
...) at submission time regardless of who would approve it - that class
of write is categorically different from a maintenance record, and
closing it off early is cheap insurance on top of the ORM/ACL boundary
the design doc treats as sufficient for everything else.

A failed execution (bad JSON, an ORM validation error, ...) is recorded
in ``error_message`` with ``state = 'failed'`` - never re-raised past
``_execute()`` - so the approval itself and the failure are both
preserved in the audit trail, not lost to a rolled-back transaction.
