from odoo import fields, models


class DeployfleetAIResponseCache(models.Model):
    """Short-TTL, exact-match cache: hashes (feature + system_prompt +
    user_message) and skips the provider call entirely on a hit. This is
    the source's `security.ai.cache` pattern, kept close to verbatim per
    docs/architecture/02-reuse-strategy.md §0.
    """

    _name = "deployfleet.ai.response.cache"
    _description = "DeployFleet AI Response Cache"
    _order = "create_date desc"
    _rec_name = "feature"

    cache_key = fields.Char(required=True, index=True, help="SHA-256 of feature + system_prompt + user_message.")
    feature = fields.Char(required=True)
    response = fields.Text(required=True)
    hit_count = fields.Integer(default=0)

    _sql_constraints = [
        ("cache_key_unique", "UNIQUE(cache_key)", "Cache key must be unique."),
    ]

    def action_clear_all(self):
        # Deliberate full-table clear, admin-triggered from the cache list view —
        # not a hot path, and the whole point is to delete every entry.
        all_entries = self.search([])  # pylint: disable=no-search-all
        count = len(all_entries)
        all_entries.unlink()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Cache Cleared",
                "message": f"Deleted {count} response cache entries.",
                "type": "success",
            },
        }


class DeployfleetAIContextCache(models.Model):
    """Long-TTL cache for slow-changing, per-entity context (e.g. a
    vehicle's spec/maintenance history) — the split this doc's revision
    added on top of the source's single-tier cache (see
    docs/architecture/08-ai-architecture.md §3): a fuel-anomaly query about
    the same truck shouldn't re-send its full profile on every call, only
    the new fuel reading.

    `context_key` should include an entity-version marker (e.g.
    "vehicle:123:v5") so a stale profile invalidates naturally once the
    entity actually changes, rather than only on a fixed timer.
    """

    _name = "deployfleet.ai.context.cache"
    _description = "DeployFleet AI Context Cache"
    _order = "create_date desc"
    _rec_name = "context_key"

    context_key = fields.Char(required=True, index=True)
    feature = fields.Char(required=True)
    content = fields.Text(required=True)
    expires_at = fields.Datetime(required=True, index=True)

    _sql_constraints = [
        ("context_key_unique", "UNIQUE(context_key)", "Context cache key must be unique."),
    ]

    def _is_expired(self):
        self.ensure_one()
        return bool(self.expires_at) and self.expires_at < fields.Datetime.now()

    def action_clear_expired(self):
        expired = self.search([("expires_at", "<", fields.Datetime.now())])
        count = len(expired)
        expired.unlink()
        return count
