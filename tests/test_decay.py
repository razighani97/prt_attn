"""The decay fits must recover known answers from simulated data."""

import numpy as np

from protest_attention.analyse.decay import MODELS, bootstrap, fit

T = np.arange(200, dtype=float)
B = 500.0


def _simulate(model: str, shape_param: float, a: float = 50_000, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    p = np.array([np.log(a), np.log(shape_param)])
    mu = B + a * MODELS[model][0](T, p)
    return rng.poisson(mu).astype(float)


def test_exponential_half_life_recovered():
    y = _simulate("exponential", 10.0)  # tau 10 -> half-life 6.93
    f = fit(T, y, B, "exponential", a0=y[0] - B)
    assert abs(f["half_life"] - 10 * np.log(2)) < 0.2


def test_power_law_half_life_recovered():
    y = _simulate("power_law", 1.2)  # half-life 2^(1/1.2) - 1 = 0.78
    f = fit(T, y, B, "power_law", a0=y[0] - B)
    assert abs(f["half_life"] - (2 ** (1 / 1.2) - 1)) < 0.05


def test_aic_picks_the_true_model():
    for true, param in (("exponential", 10.0), ("power_law", 1.2)):
        y = _simulate(true, param)
        aic = {m: fit(T, y, B, m, a0=y[0] - B)["aic"] for m in MODELS}
        assert min(aic, key=aic.get) == true


def test_bootstrap_interval_covers_truth():
    y = _simulate("exponential", 10.0, a=5_000, seed=3)
    f = fit(T, y, B, "exponential", a0=y[0] - B)
    boot = bootstrap(T, y, B, "exponential", f, np.random.default_rng(0), n_boot=200)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    assert lo < 10 * np.log(2) < hi
