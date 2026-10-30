#!/usr/bin/env python3
"""Independent re-check of out/results.json with a separately written state-vector QAOA.

It does not call Sim9_2.qaoa_probs: the circuit is rebuilt here from the definition in the paper,
psi = prod_k M(beta_k) U(gamma_k) psi0, U(gamma) = exp(-i gamma E / s), M(beta) = exp(-i beta sum_j X_j),
with theta = (gamma_1..gamma_p, beta_1..beta_p). Only the cached energy and outcome tables are shared.
Every frozen and tuned value in out/results.json is recomputed; the random sensitivity draws are not repeated.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from load import PAIRINGS  # noqa: E402
from tables import pairing_table  # noqa: E402


def state(E, s, theta, n):
    p = len(theta) // 2
    psi = np.full(1 << n, 2 ** (-n / 2), dtype=complex)
    for k in range(p):
        psi = psi * np.exp(-1j * theta[k] * E / s)
        c, sn = np.cos(theta[p + k]), np.sin(theta[p + k])
        for q in range(n):
            v = psi.reshape(-1, 2, 1 << q)
            a, b = v[:, 0, :].copy(), v[:, 1, :].copy()
            v[:, 0, :] = c * a - 1j * sn * b
            v[:, 1, :] = c * b - 1j * sn * a
    return np.abs(psi) ** 2


def main():
    res = json.loads((HERE / "out" / "results.json").read_text())["pairings"]
    worst = 0.0
    for letter, case, method in PAIRINGS:
        key = f"{letter} {'QUBO' if method == 'galle' else 'predicate'}"
        if key not in res:
            continue
        t = pairing_table(case, method)
        r = res[key]
        checks = [("frozen p2", t["theta"], r["frozen_p2"])]
        for kind in ("tuned_energy", "tuned_optimal"):
            for p, d in r.get(kind, {}).items():
                checks.append((f"{kind} p{p}", np.array(d["theta"]), d))
        for name, th, d in checks:
            P = state(t["E"], t["scale"], np.asarray(th, float), t["n"])
            assert abs(P.sum() - 1) < 1e-9
            got = dict(P_legal=P[t["accepted"]].sum(), P_optimal=P[t["optimal"]].sum(), mean_E=P @ t["E"])
            diff = max(abs(got[k] - d[k]) for k in got)
            worst = max(worst, diff)
            if diff > 1e-9:
                print("MISMATCH", key, name, {k: (float(got[k]), d[k]) for k in got})
        # ground strings are optimal plans (the lowest energy is a legal optimal plan)
        ground = t["E"] == t["E"].min()
        print(key, "checked", len(checks), "| ground strings optimal:", bool(t["optimal"][ground].all()),
              f"| ground {int(ground.sum())} of {int(t['optimal'].sum())} optimal strings")
    print("largest difference", worst)


if __name__ == "__main__":
    main()
