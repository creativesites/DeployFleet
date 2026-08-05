from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetHelpSearch(TransactionCase):
    def setUp(self):
        super().setUp()
        self.category = self.env["deployfleet.help.category"].create({
            "name": "Search Category", "slug": "search-category",
        })
        self.tag = self.env["deployfleet.help.tag"].create({"name": "invoice"})
        self.title_match = self.env["deployfleet.help.article"].create({
            "name": "How invoices work", "slug": "how-invoices-work", "category_id": self.category.id,
            "summary": "Billing basics",
        })
        self.body_match = self.env["deployfleet.help.article"].create({
            "name": "Getting Paid", "slug": "getting-paid", "category_id": self.category.id,
            "summary": "Payments and receivables",
            "body": "<p>Once a delivery is confirmed, an invoice is created automatically.</p>",
        })
        self.tag_match = self.env["deployfleet.help.article"].create({
            "name": "Billing Overview", "slug": "billing-overview", "category_id": self.category.id,
            "tag_ids": [(6, 0, [self.tag.id])],
        })
        self.no_match = self.env["deployfleet.help.article"].create({
            "name": "Unrelated Article", "slug": "unrelated-article", "category_id": self.category.id,
            "summary": "Nothing to do with the search term",
        })

    def test_empty_query_returns_empty(self):
        self.assertFalse(self.env["deployfleet.help.article"].search_help(""))
        self.assertFalse(self.env["deployfleet.help.article"].search_help(None))

    def test_title_match_ranked_first(self):
        results = self.env["deployfleet.help.article"].search_help("invoice")
        self.assertIn(self.title_match, results)
        self.assertEqual(results[0], self.title_match)

    def test_body_and_tag_matches_included(self):
        results = self.env["deployfleet.help.article"].search_help("invoice")
        self.assertIn(self.body_match, results)

    def test_tag_match_included(self):
        results = self.env["deployfleet.help.article"].search_help("invoice")
        self.assertIn(self.tag_match, results)

    def test_unrelated_article_excluded(self):
        results = self.env["deployfleet.help.article"].search_help("invoice")
        self.assertNotIn(self.no_match, results)

    def test_limit_respected(self):
        results = self.env["deployfleet.help.article"].search_help("invoice", limit=1)
        self.assertEqual(len(results), 1)
