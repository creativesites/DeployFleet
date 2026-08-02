from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetCore(TransactionCase):
    def test_module_category_installed(self):
        category = self.env.ref("deployfleet_core.module_category_deployfleet")
        self.assertEqual(category.name, "DeployFleet")

    def test_root_menu_installed(self):
        menu = self.env.ref("deployfleet_core.menu_deployfleet_root")
        self.assertEqual(menu.name, "DeployFleet")

    def test_sequence_mixin_generates_reference(self):
        self.env["ir.sequence"].create({
            "name": "Test Sequence",
            "code": "deployfleet.test.sequence",
            "prefix": "TST",
            "padding": 4,
        })
        mixin = self.env["deployfleet.sequence.mixin"]
        reference = mixin._deployfleet_next_reference("deployfleet.test.sequence")
        self.assertTrue(reference.startswith("TST"))

    def test_sequence_mixin_raises_on_missing_sequence(self):
        mixin = self.env["deployfleet.sequence.mixin"]
        with self.assertRaises(ValueError):
            mixin._deployfleet_next_reference("deployfleet.does.not.exist")

    def test_seed_vehicle_types_installed(self):
        rigid = self.env.ref("deployfleet_core.vehicle_type_rigid")
        self.assertEqual(rigid.code, "rigid")
        articulated = self.env.ref("deployfleet_core.vehicle_type_articulated")
        self.assertEqual(articulated.code, "articulated")

    def test_vehicle_type_name_must_be_unique(self):
        with self.assertRaises(Exception):
            self.env["deployfleet.vehicle.type"].create({"name": "Rigid Truck"})
