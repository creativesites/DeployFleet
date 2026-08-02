from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDeployfleetRoute(TransactionCase):
    def setUp(self):
        super().setUp()
        self.lusaka = self.env["deployfleet.depot"].create({"name": "Lusaka Depot"})
        self.kitwe = self.env["deployfleet.depot"].create({"name": "Kitwe Depot"})

    def test_create_route(self):
        route = self.env["deployfleet.route"].create({
            "name": "Lusaka -> Kitwe",
            "origin_depot_id": self.lusaka.id,
            "destination_depot_id": self.kitwe.id,
            "distance_km": 320.0,
        })
        self.assertEqual(route.distance_km, 320.0)

    def test_origin_and_destination_must_differ(self):
        with self.assertRaises(ValidationError):
            self.env["deployfleet.route"].create({
                "name": "Bad Route",
                "origin_depot_id": self.lusaka.id,
                "destination_depot_id": self.lusaka.id,
            })

    def test_route_stops_ordered_by_sequence(self):
        route = self.env["deployfleet.route"].create({
            "name": "Lusaka -> Kitwe",
            "origin_depot_id": self.lusaka.id,
            "destination_depot_id": self.kitwe.id,
        })
        ndola = self.env["deployfleet.depot"].create({"name": "Ndola Depot"})
        self.env["deployfleet.route.stop"].create({"route_id": route.id, "sequence": 20, "depot_id": ndola.id})
        self.env["deployfleet.route.stop"].create({"route_id": route.id, "sequence": 10, "depot_id": self.lusaka.id})
        self.assertEqual(route.stop_ids[0].depot_id, self.lusaka)
        self.assertEqual(route.stop_ids[1].depot_id, ndola)
