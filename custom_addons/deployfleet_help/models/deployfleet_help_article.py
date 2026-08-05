from odoo import api, fields, models


class DeployfleetHelpArticle(models.Model):
    """The single content unit for every Help Center content type — plain
    guides, per-module guides, FAQ entries, and troubleshooting entries
    are all structurally "a title plus a plain-language body", so they
    share one model distinguished by `content_type` rather than four
    separate models each duplicating search/tagging/related-articles/
    role-relevance.

    `body` is `fields.Html` (Odoo's standard rich-content field, with
    the built-in sanitizer) rather than Text/Markdown — there is no
    markdown renderer anywhere in deployfleet_ui's asset bundle, and
    Html is the same mechanism Odoo's own Knowledge/Website apps use
    for this exact kind of rich-but-safe content, with a ready-made
    authoring widget in the backend form.

    `_inherit = ["mail.thread"]` gives a free, real change-history/audit
    trail (who changed what, when) via Odoo's own chatter, covering
    "future versioning" without a bespoke version-snapshot model.
    """

    _name = "deployfleet.help.article"
    _description = "DeployFleet Help Article"
    _inherit = ["mail.thread"]
    _order = "sequence, name"

    name = fields.Char(required=True, tracking=True)
    slug = fields.Char(required=True, index=True, help="Stable key for deep-links, independent of the title.")
    category_id = fields.Many2one("deployfleet.help.category", required=True, tracking=True)
    content_type = fields.Selection(
        [
            ("guide", "Guide"),
            ("module_guide", "Module Guide"),
            ("faq", "FAQ"),
            ("troubleshooting", "Troubleshooting"),
        ],
        default="guide", required=True, index=True,
    )
    summary = fields.Char(help="Shown as the card/search-result subtitle.")
    body = fields.Html(sanitize=True, tracking=True)
    tag_ids = fields.Many2many("deployfleet.help.tag")
    related_article_ids = fields.Many2many(
        "deployfleet.help.article",
        "deployfleet_help_article_related_rel", "article_id", "related_id",
        string="Related Articles",
    )
    related_workflow_id = fields.Many2one(
        "deployfleet.help.workflow", help="Lets a Module Guide point at its own workflow diagram.",
    )
    role_group_ids = fields.Many2many(
        "res.groups", string="Relevant Roles",
        help="Which deployfleet_security role(s) this article is most relevant to, for role-based Help Center "
             "recommendations. Leave empty to show it to everyone.",
    )
    context_key = fields.Char(
        index=True,
        help="Article-level deep-link key, overriding the category's own context_key when a workspace should "
             "land on this one specific article rather than browsing its whole category.",
    )
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    view_count = fields.Integer(default=0, help="Incremented on read — a cheap usage/relevance signal.")

    _sql_constraints = [
        ("slug_unique", "UNIQUE(slug)", "This slug is already in use by another article."),
    ]

    def action_register_view(self):
        self.ensure_one()
        self.sudo().view_count += 1

    @api.model
    def search_help(self, query, limit=20):
        """Simple ILIKE search across title/summary/body/tags, ranked
        title-match-first. Correct-sized for the content volume this
        module actually seeds today — a Postgres full-text-search
        upgrade is a documented future enhancement, not built
        speculatively now (no full-text-search precedent exists
        anywhere else in this codebase either)."""
        query = (query or "").strip()
        if not query:
            return self.browse()
        title_matches = self.search([("name", "ilike", query)], limit=limit)
        if len(title_matches) >= limit:
            return title_matches
        other_matches = self.search(
            [
                "|", "|", ("summary", "ilike", query), ("body", "ilike", query), ("tag_ids.name", "ilike", query),
                ("id", "not in", title_matches.ids),
            ],
            limit=limit - len(title_matches),
        )
        return title_matches | other_matches
