"""Exact energy and outcome tables for the eight IBM pairings (cached as .npz)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import PAIRINGS, sim9  # noqa: E402

CACHE = Path(__file__).resolve().parent / "cache"


def pairing_table(case, method):
    """Return dict(E, accepted, optimal, n, scale, theta, angle_id, uniform_legal, uniform_opt)."""
    CACHE.mkdir(exist_ok=True)
    f = CACHE / f"{case}_{method}.npz"
    m = sim9()
    bay, problem, theta, angle_id = m.ibm_build(case, method)
    if f.exists():
        z = np.load(f)
        E, acc, cost = z["E"], z["accepted"], z["cost"]
    else:
        t = m.evaluation_table(problem)
        E, acc, cost = t["E"], t["accepted"], t["cost"]
        np.savez(f, E=E, accepted=acc, cost=cost)
    opt_cost = int(cost[acc].min())
    if opt_cost != bay["optimum_for_scoring_only"]:
        raise RuntimeError(f"{case}: enumerated optimum {opt_cost} differs from the proven optimum")
    optimal = acc & (cost == opt_cost)
    n = problem.n
    return dict(E=np.asarray(E, float), accepted=acc, optimal=optimal, cost=cost, n=n, scale=float(problem.scale),
                theta=np.array(theta, float), angle_id=angle_id, uniform_legal=acc.mean(), uniform_opt=optimal.mean(),
                problem=problem, bay=bay)


def all_tables():
    return {(letter, method): pairing_table(case, method) for letter, case, method in PAIRINGS}
