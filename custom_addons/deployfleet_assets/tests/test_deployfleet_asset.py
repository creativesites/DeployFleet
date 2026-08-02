from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetAsset(TransactionCase):
    def test_default_status_is_in_service(self):
        asset = self.env["deployfleet.asset"].create({"name": "Trailer A", "asset_type": "trailer"})
        self.assertEqual(asset.status, "in_service")

    def test_status_transition_actions(self):
        asset = self.env["deployfleet.asset"].create({"name": "Trailer A", "asset_type": "trailer"})
        asset.action_set_under_repair()
        self.assertEqual(asset.status, "under_repair")
        asset.action_set_in_storage()
        self.assertEqual(asset.status, "in_storage")
        asset.action_set_retired()
        self.assertEqual(asset.status, "retired")
        asset.action_set_in_service()
        self.assertEqual(asset.status, "in_service")
