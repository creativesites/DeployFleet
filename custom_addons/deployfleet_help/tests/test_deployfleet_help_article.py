from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetHelpArticle(TransactionCase):
    def setUp(self):
        super().setUp()
        self.category = self.env["deployfleet.help.category"].create({
            "name": "Test Category", "slug": "test-category",
        })

    def _create_article(self, **extra):
        vals = {"name": "Test Article", "slug": "test-article", "category_id": self.category.id}
        vals.update(extra)
        return self.env["deployfleet.help.article"].create(vals)

    def test_slug_unique(self):
        self._create_article()
        with self.assertRaises(Exception):
            self._create_article(name="Another Article")

    def test_view_count_increments(self):
        article = self._create_article()
        self.assertEqual(article.view_count, 0)
        article.action_register_view()
        self.assertEqual(article.view_count, 1)

    def test_driver_can_read_article(self):
        article = self._create_article()
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        driver_user = self.env["res.users"].create({
            "name": "Help Driver User", "login": "help_driver_user@example.com",
            "email": "help_driver_user@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        # Should not raise.
        article.with_user(driver_user).read(["name"])

    def test_driver_cannot_write_article(self):
        article = self._create_article()
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        driver_user = self.env["res.users"].create({
            "name": "Help Driver User 2", "login": "help_driver_user_2@example.com",
            "email": "help_driver_user_2@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        with self.assertRaises(AccessError):
            article.with_user(driver_user).write({"name": "Hacked"})

    def test_manager_can_write_article(self):
        article = self._create_article()
        manager_group = self.env.ref("deployfleet_security.group_deployfleet_manager")
        manager_user = self.env["res.users"].create({
            "name": "Help Manager User", "login": "help_manager_user@example.com",
            "email": "help_manager_user@example.com", "group_ids": [(6, 0, [manager_group.id])],
        })
        article.with_user(manager_user).write({"name": "Updated by manager"})
        self.assertEqual(article.name, "Updated by manager")
