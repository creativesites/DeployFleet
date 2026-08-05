=========================
DeployFleet Help Center
=========================

In-app Help Center content: categories (``deployfleet.help.category``),
articles (``deployfleet.help.article`` — guides, module guides, FAQ, and
troubleshooting all share one model via ``content_type``, since they're
all structurally "a title plus a plain-language body"), workflow
diagrams (``deployfleet.help.workflow`` / ``.workflow.step``), and a
first-time-setup checklist (``deployfleet.help.checklist`` /
``.checklist.item`` / ``.checklist.progress``) per
``docs/architecture/22-help-center-architecture.md``.

Depends on ``deployfleet_security`` only. All frontend (the Help Center
screen, the persistent Help trigger, Mega Menu/Launcher/Command Palette
wiring, contextual Help buttons) lives in ``deployfleet_ui`` — this
module is content and data only, matching how ``deployfleet_leave`` and
every other content module in this codebase is split.

``body`` is ``fields.Html(sanitize=True)`` rather than Markdown — there
is no markdown renderer anywhere in ``deployfleet_ui``'s asset bundle,
and Html is the same rich-content mechanism Odoo's own Knowledge/Website
apps use, with a ready-made authoring widget in the backend form.
``deployfleet.help.article`` inherits ``mail.thread`` for a free,
real change-history/audit trail, covering "future versioning" without a
bespoke snapshot model.

No ``company_id`` anywhere in this module — Help Center content
documents how to use the product, which is identical for every company
on a deployment, unlike the operational data the C-01 multi-company
audit fix was about. The one per-user model,
``deployfleet.help.checklist.progress``, is ``ir.rule``-scoped to the
user's own rows via ``deployfleet_help_checklist_progress_rule_own``.
