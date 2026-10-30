"""Check: the frozen p=2 angles reproduce the paper's ideal legal and optimal probabilities (Table 6)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from load import sim9  # noqa: E402
from tables import all_tables  # noqa: E402

PAPER = {("A", "predicate"): (24.86, 8.66), ("A", "galle"): (24.55, 12.66), ("B", "predicate"): (10.31, 3.46),
         ("B", "galle"): (8.78, 3.47), ("C", "predicate"): (11.46, 3.76), ("C", "galle"): (10.99, 4.82),
         ("D", "predicate"): (10.44, 9.21), ("E", "predicate"): (4.25, 1.27)}
m = sim9()
for key, t in all_tables().items():
    P = m.qaoa_probs(t["E"], t["theta"], 2, t["scale"], t["n"])
    legal, opt = 100 * P[t["accepted"]].sum(), 100 * P[t["optimal"]].sum()
    pl, po = PAPER[key]
    print(f"{key[0]} {key[1]:9s} n={t['n']:2d} scale={t['scale']:7.2f} uniform {100*t['uniform_legal']:.3f}/{100*t['uniform_opt']:.3f} "
          f"ideal legal {legal:6.2f} (paper {pl:5.2f})  optimal {opt:6.2f} (paper {po:5.2f})  "
          f"{'OK' if abs(legal-pl)<0.006 and abs(opt-po)<0.006 else 'MISMATCH'}  legal strings {int(t['accepted'].sum())}, optimal {int(t['optimal'].sum())}")
