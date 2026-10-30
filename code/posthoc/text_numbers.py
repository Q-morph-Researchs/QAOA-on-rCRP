#!/usr/bin/env python3
"""Print every number that Section 3.6, 3.8, 3.11 and the response file quote, straight from out/results.json."""
import json
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "out" / "results.json").read_text())["pairings"]
ORDER = ["A predicate", "A QUBO", "B predicate", "B QUBO", "C predicate", "C QUBO", "D predicate", "E predicate"]
SA_OPT = {"A predicate": 7.93, "A QUBO": 25.99, "B predicate": 5.10, "B QUBO": 5.19, "C predicate": 10.48,
          "C QUBO": 13.63, "D predicate": 20.80, "E predicate": 7.53}           # Table 5
HW_OPT = {"A predicate": 3.54, "A QUBO": 6.28, "B predicate": 1.11, "B QUBO": 0.69, "C predicate": 0.68,
          "C QUBO": 1.73, "D predicate": 7.27, "E predicate": 0.34}             # Table 4


def r2(x):
    return float(Decimal(repr(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pc(x):
    return r2(100 * x)


def rng(vals):
    return f"{min(vals):.2f}–{max(vals):.2f}"


frozen = {k: pc(R[k]["frozen_p2"]["P_optimal"]) for k in ORDER}
print("frozen p2 optimal", frozen)

print("\nSensitivity (relative to frozen, 5th–95th percentile):")
for d in ("0.05", "0.10"):
    rel = {k: (R[k]["sensitivity"][d]["P_optimal"]["p05"] / R[k]["frozen_p2"]["P_optimal"],
               R[k]["sensitivity"][d]["P_optimal"]["p95"] / R[k]["frozen_p2"]["P_optimal"]) for k in ORDER}
    print(" ±" + d, {k: (round(a, 2), round(b, 2)) for k, (a, b) in rel.items()})
    six = [k for k in ORDER if k not in ("D predicate", "E predicate")]
    print("   six pairings (not D, E):", round(min(rel[k][0] for k in six), 2), "to", round(max(rel[k][1] for k in six), 2))
    leg = {k: (R[k]["sensitivity"][d]["P_legal"]["p05"] / R[k]["frozen_p2"]["P_legal"],
               R[k]["sensitivity"][d]["P_legal"]["p95"] / R[k]["frozen_p2"]["P_legal"]) for k in ORDER}
    print("   legal relative", {k: (round(a, 2), round(b, 2)) for k, (a, b) in leg.items()})

for kind in ("energy", "optimal"):
    t = {k: R[k][f"tuned_{kind}"] for k in ORDER}
    print(f"\nTuned for {kind}:")
    for p in ("1", "2", "3", "4", "5"):
        o = {k: pc(t[k][p]["P_optimal"]) for k in ORDER}
        l = {k: pc(t[k][p]["P_legal"]) for k in ORDER}
        print(f" p{p} optimal {o}  range {rng(o.values())}")
        print(f"    legal   {l}  range {rng(l.values())}")
        above_sa = [k for k in ORDER if o[k] > SA_OPT[k]]
        print(f"    above SA optimal-candidate fraction: {len(above_sa)} {above_sa}")
    ratio2 = {k: round(t[k]["2"]["P_optimal"] / R[k]["frozen_p2"]["P_optimal"], 2) for k in ORDER}
    print(" p2 / frozen ratio", ratio2)
    mono = {k: all(t[k][str(p + 1)]["P_optimal"] >= t[k][str(p)]["P_optimal"] - 1e-12 for p in range(1, 5)) for k in ORDER}
    emono = {k: all(t[k][str(p + 1)]["mean_E"] <= t[k][str(p)]["mean_E"] + 1e-9 for p in range(1, 5)) for k in ORDER}
    print(" optimal probability never falls with p:", mono)
    print(" mean energy never rises with p:", emono)
    print(" sources:", {k: [t[k][p]["source"] for p in ("1", "2", "3", "4", "5")] for k in ORDER})
    print(" seconds:", {k: [t[k][p]["seconds"] for p in ("1", "2", "3", "4", "5")] for k in ORDER})

cx = {k: R[k]["logical_cx"]["1"] for k in ORDER}
print("\nlogical two-qubit gates per layer", cx, "range", min(cx.values()), "–", max(cx.values()))
print("ground strings / optimal strings", {k: (R[k]["ground_strings"], R[k]["optimal_strings"]) for k in ORDER})
print("SA above frozen ideal:", [k for k in ORDER if SA_OPT[k] > frozen[k]])
ret = {k: round(HW_OPT[k] / frozen[k], 3) for k in ORDER}
print("hardware retention", ret)
