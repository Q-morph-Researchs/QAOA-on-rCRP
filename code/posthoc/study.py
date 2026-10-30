#!/usr/bin/env python3
"""Post-hoc noiseless study of the eight IBM pairings: angle sensitivity, tuned angles and depth.

Everything here is a noiseless state-vector calculation on the sealed Sim9_2.py energy tables
(hash-checked in load.py). The frozen p = 2 angles reproduce the paper's ideal probabilities
exactly (reproduce.py). No hardware job is run and the IBM study is not changed.

Three questions, for every pairing:
  1. Sensitivity: how much do the ideal legal and optimal probabilities change when each frozen
     angle is moved at random by up to 0.05 or 0.10 rad?
  2. Tuned angles: what do angles chosen for this pairing alone give at p = 1..5, when they
     (a) minimise the mean energy, the usual QAOA target, which needs no knowledge of the optimum, or
     (b) maximise the probability of an optimal plan directly, a reference that uses the known
         optimal bit strings and so is not a usable solver?
  3. Depth: how do these numbers grow from p = 1 to p = 5, and what does each layer cost in
     logical two-qubit gates?
Tuned values are the best found from many starts (grid seeds, the frozen vector, warm starts from
p - 1 with an idle layer added, and random starts); they are not proven global optima.

Usage: python3 -I study.py [out_dir]
"""
import json
import math
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from load import EXPECTED, PAIRINGS, sim9  # noqa: E402
from tables import pairing_table  # noqa: E402

PMAX = 5
DELTAS = (0.05, 0.10)
SENS_DRAWS = 2000
RANDOM_STARTS = {1: 48, 2: 48, 3: 32, 4: 32, 5: 32}
GRID = {1: (121, 61), 2: 12}        # p = 1: gamma x beta points; p = 2: points per angle
GRID_SEEDS = 16                     # best grid points refined as extra starts
SEED = 2026102001


def probs(t, theta, p):
    return sim9().qaoa_probs(t["E"], np.asarray(theta, float), p, t["scale"], t["n"])


def measures(t, theta, p):
    P = probs(t, theta, p)
    return dict(P_legal=float(P[t["accepted"]].sum()), P_optimal=float(P[t["optimal"]].sum()),
                P_ground=float(P[t["E"] == t["E"].min()].sum()), mean_E=float(P @ t["E"]))


def objective(t, p, kind):
    E, opt = t["E"], t["optimal"]
    if kind == "energy":
        return lambda th: float(probs(t, th, p) @ E) / t["scale"]
    return lambda th: -float(probs(t, th, p)[opt].sum())


def interp_start(prev, p):
    """INTERP warm start: stretch the p - 1 schedule to p layers (Zhou et al.)."""
    q = p - 1
    g, b = prev[:q], prev[q:]
    x = np.linspace(0, 1, p)
    xp = np.linspace(0, 1, q) if q > 1 else np.array([0.0])
    gi = np.interp(x, xp, g) if q > 1 else np.full(p, g[0])
    bi = np.interp(x, xp, b) if q > 1 else np.full(p, b[0])
    return np.r_[gi, bi]


def grid_starts(t, p, f):
    if p == 1:
        ng, nb = GRID[1]
        G, B = np.meshgrid(np.linspace(-math.pi, math.pi, ng), np.linspace(-math.pi / 2, math.pi / 2, nb), indexing="ij")
        pts = np.c_[G.ravel(), B.ravel()]
    else:
        k = GRID[2]
        g = np.linspace(-math.pi, math.pi, k, endpoint=False)
        b = np.linspace(-math.pi / 2, math.pi / 2, k, endpoint=False)
        mesh = np.meshgrid(g, g, b, b, indexing="ij")
        pts = np.stack([m.ravel() for m in mesh], axis=1)
    vals = np.array([f(x) for x in pts])
    return [pts[i] for i in np.argsort(vals)[:GRID_SEEDS]]


def tune_task(args):
    letter, case, method, kind = args
    t = pairing_table(case, method)
    rng = np.random.default_rng([SEED, ord(letter), len(method), len(kind)])
    out, prev = {}, None
    for p in range(1, PMAX + 1):
        f = objective(t, p, kind)
        starts = []
        if p == 2:
            starts.append(("frozen", t["theta"]))
        if prev is not None:
            starts.append(("interp", interp_start(prev, p)))
            # the previous optimum plus an idle layer (gamma = beta = 0) gives the same state,
            # so the best value found can never get worse as p grows
            starts.append(("pad", np.r_[prev[:p - 1], 0.0, prev[p - 1:], 0.0]))
        if p in GRID:
            starts += [("grid", s) for s in grid_starts(t, p, f)]
        for _ in range(RANDOM_STARTS[p]):
            starts.append(("random", np.r_[rng.uniform(-math.pi, math.pi, p), rng.uniform(-math.pi / 2, math.pi / 2, p)]))
        best, best_src, nfev, t0 = None, None, 0, time.perf_counter()
        for src, x0 in starts:
            r = minimize(f, np.asarray(x0, float), method="L-BFGS-B", options=dict(maxiter=1000))
            nfev += r.nfev
            if best is None or r.fun < best.fun - 1e-12:
                best, best_src = r, src
        prev = best.x
        out[p] = dict(theta=[float(v) for v in best.x], source=best_src, starts=len(starts), evaluations=int(nfev),
                      seconds=round(time.perf_counter() - t0, 1), **measures(t, best.x, p))
    return (letter, method, kind), out


def sensitivity(t):
    rng = np.random.default_rng([SEED, 7])
    res = {}
    for d in DELTAS:
        po, pl = [], []
        for _ in range(SENS_DRAWS):
            mm = measures(t, t["theta"] + rng.uniform(-d, d, 4), 2)
            po.append(mm["P_optimal"]); pl.append(mm["P_legal"])
        po, pl = np.array(po), np.array(pl)
        q = lambda a: dict(min=float(a.min()), p05=float(np.quantile(a, .05)), median=float(np.median(a)),
                           p95=float(np.quantile(a, .95)), max=float(a.max()))
        res[f"{d:.2f}"] = dict(P_optimal=q(po), P_legal=q(pl), draws=SENS_DRAWS)
    return res


def main(out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    m = sim9()
    results = dict(meta=dict(sim9_sha256=EXPECTED, numpy=np.__version__, seed=SEED, pmax=PMAX, deltas=DELTAS,
                             sensitivity_draws=SENS_DRAWS, random_starts=RANDOM_STARTS, grid=GRID, grid_seeds=GRID_SEEDS,
                             optimizer="scipy L-BFGS-B, finite-difference gradient, maxiter 1000",
                             note="noiseless state-vector values; tuned values are best found, not proven optima"),
                   pairings={})
    for letter, case, method in PAIRINGS:
        t = pairing_table(case, method)
        key = f"{letter} {'QUBO' if method == 'galle' else 'predicate'}"
        results["pairings"][key] = dict(
            instance=case, method=method, n=t["n"], scale=t["scale"], angle_id=t["angle_id"],
            uniform_legal=float(t["uniform_legal"]), uniform_optimal=float(t["uniform_opt"]),
            optimal_strings=int(t["optimal"].sum()), ground_strings=int((t["E"] == t["E"].min()).sum()),
            frozen_p2=measures(t, t["theta"], 2), sensitivity=sensitivity(t),
            logical_cx={p: m.logical_two_qubit_gates(t["problem"], p)["cx"] for p in range(1, PMAX + 1)})
        print(key, "frozen", results["pairings"][key]["frozen_p2"], flush=True)
    tasks = [(l, c, me, k) for l, c, me in PAIRINGS for k in ("energy", "optimal")]
    tasks.sort(key=lambda a: -pairing_table(a[1], a[2])["n"])          # largest registers first
    with Pool(4) as pool:
        for (letter, method, kind), out in pool.imap_unordered(tune_task, tasks):
            key = f"{letter} {'QUBO' if method == 'galle' else 'predicate'}"
            results["pairings"][key][f"tuned_{kind}"] = out
            print(key, kind, {p: round(100 * v["P_optimal"], 2) for p, v in out.items()}, flush=True)
            (out_dir / "results.json").write_text(json.dumps(results, indent=1))
    (out_dir / "results.json").write_text(json.dumps(results, indent=1))
    return results


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "out")
