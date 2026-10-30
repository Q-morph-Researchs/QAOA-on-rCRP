#!/usr/bin/env python3
"""Turn out/results.json into the paper's Table 7 (tables2/TS.md) and print the numbers the text quotes."""
import json
from decimal import ROUND_HALF_UP, Decimal
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = json.loads((HERE / "out" / "results.json").read_text())
ORDER = ["A predicate", "A QUBO", "B predicate", "B QUBO", "C predicate", "C QUBO", "D predicate", "E predicate"]
SA_OPT = {"A predicate": 7.93, "A QUBO": 25.99, "B predicate": 5.10, "B QUBO": 5.19, "C predicate": 10.48,
          "C QUBO": 13.63, "D predicate": 20.80, "E predicate": 7.53}           # Table 5
HW_OPT = {"A predicate": 3.54, "A QUBO": 6.28, "B predicate": 1.11, "B QUBO": 0.69, "C predicate": 0.68,
          "C QUBO": 1.73, "D predicate": 7.27, "E predicate": 0.34}             # Table 4


def pct(x, d=2):
    """Percent with halves rounded up, as in the paper's tables (8/256 = 3.125% -> 3.13)."""
    q = Decimal(repr(100 * x)).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    if q == 0 and x > 0:
        return f"<{Decimal(1).scaleb(-d)}"                 # e.g. 7e-6 -> "<0.01", not "0.00"
    return f"{q:.{d}f}"


def main(dest):
    rows = ["| Pairing | Uniform | Frozen, p = 2 | Moved, 5th–95th percentile | Energy-tuned, p = 2 | "
            "Energy-tuned, p = 5 | Optimal-plan probability maximized, p = 2 | Optimal-plan probability "
            "maximized, p = 5 | Two-qubit gates per layer |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k in ORDER:
        r = RES["pairings"][k]
        s = r["sensitivity"]["0.10"]["P_optimal"]
        e, o = r["tuned_energy"], r["tuned_optimal"]
        cx = r["logical_cx"]
        per_layer = cx["2"] // 2 if isinstance(next(iter(cx)), str) else cx[2] // 2
        rows.append(f"| {k} | {pct(r['uniform_optimal'])} | {pct(r['frozen_p2']['P_optimal'])} | "
                    f"{pct(s['p05'])}–{pct(s['p95'])} | {pct(e['2']['P_optimal'])} | {pct(e['5']['P_optimal'])} | "
                    f"{pct(o['2']['P_optimal'])} | {pct(o['5']['P_optimal'])} | {per_layer} |")
    Path(dest).write_text("\n".join(rows) + "\n")
    print("\n".join(rows))

    print("\nDetail (optimal %, legal %, mean E) by depth:")
    for k in ORDER:
        r = RES["pairings"][k]
        print(k, "frozen", pct(r["frozen_p2"]["P_optimal"]), pct(r["frozen_p2"]["P_legal"]), round(r["frozen_p2"]["mean_E"], 3),
              "| SA", SA_OPT[k], "| HW", HW_OPT[k])
        for kind in ("energy", "optimal"):
            t = r[f"tuned_{kind}"]
            print("   ", kind.ljust(7), " ".join(f"p{p}:{pct(t[str(p)]['P_optimal'])}/{pct(t[str(p)]['P_legal'])}/E{t[str(p)]['mean_E']:.3f}({t[str(p)]['source']})" for p in range(1, 6)))
        for d in ("0.05", "0.10"):
            so = r["sensitivity"][d]["P_optimal"]; sl = r["sensitivity"][d]["P_legal"]
            print(f"    ±{d}: optimal {pct(so['min'])}..{pct(so['p05'])}..{pct(so['median'])}..{pct(so['p95'])}..{pct(so['max'])}"
                  f" | legal {pct(sl['p05'])}..{pct(sl['p95'])}")
        print("    cx", r["logical_cx"])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else HERE / "out" / "TS.md")
