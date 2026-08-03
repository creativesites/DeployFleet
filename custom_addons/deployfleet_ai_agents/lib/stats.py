"""Dependency-free statistical primitives shared by every Phase 5 model in
this module (predictive maintenance, fuel anomaly detection, financial
forecasting). Deliberately plain-Python closed-form formulas rather than
numpy/scikit-learn: the demo/production stack runs the stock `odoo:19.0`
image with no custom Dockerfile, so a heavy ML dependency would need an
image rebuild this project hasn't made, and would fail exactly like a
missing `requests` install if assumed present. These are honest,
real statistics (least-squares linear regression, population z-scores) -
classical statistical learning, not deep learning - which is what Phase 5's
data volume (seed data, no real pilot history yet) can actually support
without overclaiming sophistication it doesn't have. See README.rst.
"""


def zscores(values):
    """Population z-score of each value against the set's own mean/stddev.
    Returns 0.0 for every value when there's fewer than 2 points or no
    variance at all - "not enough signal to call anything an outlier" is
    always the safe default, never a fabricated one."""
    n = len(values)
    if n < 2:
        return [0.0] * n
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    stddev = variance ** 0.5
    if stddev == 0:
        return [0.0] * n
    return [(v - mean) / stddev for v in values]


def linear_regression(xs, ys):
    """Closed-form ordinary least squares. Returns (slope, intercept).
    Falls back to a flat line (slope 0) when there are fewer than two
    points or the x values have no spread - not enough data for a trend
    line to mean anything."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0, (ys[0] if ys else 0.0)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept
