====================
DeployFleet AI Core
====================

The single entry point every DeployFleet AI feature must call — no
business module is allowed to talk to an AI provider directly (see
``CLAUDE.md`` §4 and ``docs/architecture/08-ai-architecture.md``).

Provides:

- ``deployfleet.ai.core.complete(feature_key, system_prompt, user_message)``
  — the provider router, enforcing company policy, feature toggles, and
  budget limits before ever reaching a provider.
- ``deployfleet.ai.policy`` — per-company governance (AI on/off, external
  providers allowed, per-data-category blocks).
- ``deployfleet.ai.config`` — provider credentials and per-tier model
  selection (cheap vs. reasoning).
- ``deployfleet.ai.feature`` — per-feature toggles, registered as data by
  whichever module owns the feature, not hardcoded here.
- ``deployfleet.ai.response.cache`` / ``deployfleet.ai.context.cache`` —
  the split short/long-TTL cache described in the architecture doc.
- ``deployfleet.ai.usage`` / ``deployfleet.ai.budget`` — per-call cost
  logging and a pre-call budget gate.

Providers implemented: DeepSeek and OpenAI (via a shared OpenAI-compatible
adapter) and Claude (Anthropic Messages API). Gemini and a reserved
``local`` (self-hosted) slot exist in the schema but are not yet wired —
calling them raises a clear ``NotImplementedError``.

Two things this module deliberately does **not** do yet, by design: it has
no per-role AI permission scoping (coming in ``deployfleet_ai_permissions``)
and it never writes anything on an AI's behalf without a human in the loop
(the approval pipeline is ``deployfleet_ai_actions``, a later phase). Both
are described in ``docs/architecture/08-ai-architecture.md``.
