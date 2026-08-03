from odoo.tests.common import TransactionCase, tagged

from ..lib import stats


@tagged("post_install", "-at_install")
class TestStats(TransactionCase):
    def test_zscores_flat_series_are_zero(self):
        self.assertEqual(stats.zscores([5.0, 5.0, 5.0]), [0.0, 0.0, 0.0])

    def test_zscores_single_value_returns_zero(self):
        self.assertEqual(stats.zscores([42.0]), [0.0])

    def test_zscores_flags_outlier(self):
        result = stats.zscores([10.0, 10.0, 10.0, 10.0, 40.0])
        self.assertGreater(result[-1], 2.0)
        for value in result[:-1]:
            self.assertLess(abs(value), 1.0)

    def test_linear_regression_perfect_line(self):
        slope, intercept = stats.linear_regression([1, 2, 3, 4], [2, 4, 6, 8])
        self.assertAlmostEqual(slope, 2.0)
        self.assertAlmostEqual(intercept, 0.0)

    def test_linear_regression_flat_when_insufficient_points(self):
        slope, intercept = stats.linear_regression([1], [7])
        self.assertEqual(slope, 0.0)
        self.assertEqual(intercept, 7)

    def test_linear_regression_flat_when_no_x_spread(self):
        slope, intercept = stats.linear_regression([3, 3, 3], [1, 2, 3])
        self.assertEqual(slope, 0.0)
        self.assertAlmostEqual(intercept, 2.0)
