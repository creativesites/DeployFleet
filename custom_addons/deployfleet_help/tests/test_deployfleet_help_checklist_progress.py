from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetHelpChecklistProgress(TransactionCase):
    def setUp(self):
        super().setUp()
        self.checklist = self.env["deployfleet.help.checklist"].create({"name": "Test Checklist"})
        self.item = self.env["deployfleet.help.checklist.item"].create({
            "checklist_id": self.checklist.id, "title": "Do the thing",
        })
        driver_group = self.env.ref("deployfleet_security.group_deployfleet_driver")
        self.user_a = self.env["res.users"].create({
            "name": "Checklist User A", "login": "checklist_user_a@example.com",
            "email": "checklist_user_a@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })
        self.user_b = self.env["res.users"].create({
            "name": "Checklist User B", "login": "checklist_user_b@example.com",
            "email": "checklist_user_b@example.com", "group_ids": [(6, 0, [driver_group.id])],
        })

    def test_toggle_done_sets_date(self):
        progress = self.env["deployfleet.help.checklist.progress"].create({
            "user_id": self.user_a.id, "checklist_item_id": self.item.id,
        })
        self.assertFalse(progress.done)
        progress.action_toggle_done()
        self.assertTrue(progress.done)
        self.assertTrue(progress.done_date)
        progress.action_toggle_done()
        self.assertFalse(progress.done)
        self.assertFalse(progress.done_date)

    def test_unique_per_user_and_item(self):
        self.env["deployfleet.help.checklist.progress"].create({
            "user_id": self.user_a.id, "checklist_item_id": self.item.id,
        })
        with self.assertRaises(Exception):
            self.env["deployfleet.help.checklist.progress"].create({
                "user_id": self.user_a.id, "checklist_item_id": self.item.id,
            })

    def test_user_cannot_see_another_users_progress(self):
        progress_a = self.env["deployfleet.help.checklist.progress"].create({
            "user_id": self.user_a.id, "checklist_item_id": self.item.id,
        })
        visible_to_b = self.env["deployfleet.help.checklist.progress"].with_user(self.user_b).search(
            [("id", "=", progress_a.id)]
        )
        self.assertFalse(visible_to_b)

    def test_user_cannot_write_another_users_progress(self):
        progress_a = self.env["deployfleet.help.checklist.progress"].create({
            "user_id": self.user_a.id, "checklist_item_id": self.item.id,
        })
        with self.assertRaises(AccessError):
            progress_a.with_user(self.user_b).action_toggle_done()
