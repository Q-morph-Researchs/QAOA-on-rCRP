"""Sorted, analysis-ready view of the IBM rCRP results. Reads only; writes a NEW folder."""
import sys, json, math, random, sqlite3, csv, hashlib
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

D = Path.home() / "Downloads"
DB = D / "rCRP_IBM_Database_2026_10_16/ibm_results.sqlite"
COMP = D / "QAOA_Classical_Companion_2026_10_16_v1"
REF = Path(sys.argv[1]); OUT = Path(sys.argv[2])
if OUT.exists():
    sys.exit(f"{OUT} exists; refusing to overwrite")
OUT.mkdir()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True); con.row_factory = sqlite3.Row
inst = {r["case_id"]: dict(r) for r in con.execute("select * from instances")}
pair = {r["pairing_id"]: dict(r) for r in con.execute("select * from pairings")}
jobs = [dict(r) for r in con.execute("select * from job_rates")]
preps = [dict(r) for r in con.execute("select pairing_id,version,theta_json,angle_id,prepared_utc,isa_sha256 from preparations")]
ref = {r["pairing_id"]: r for r in json.load(open(REF))}
sa = {(r["case"], r["encoding"]): r for r in json.load(open(COMP / "C_sa/C_summary.json"))["rows"]}
gr = {r["case"]: r for r in json.load(open(COMP / "B_greedy/B_summary.json"))["rows"]}
mi = {r["case"]: r for r in json.load(open(COMP / "A_milp/A_summary.json"))["rows"]}
br = {(p["case"], p["encoding"]): p for p in json.load(open(COMP / "D_calibration/calibration_bridge.json"))["pairings"]}

ENC = {"predicate": "Predicate", "galle": "QUBO"}
BAY_ORDER = ["random-S3T4C6-21", "random-S3T4C6-24", "random-S4T3C6-16", "random-S3T4C7-32", "data3-3-8"]
ENC_ORDER = ["predicate", "galle"]
def pkey(pid):
    c, e = pid.split("__"); return (BAY_ORDER.index(c), ENC_ORDER.index(e))

def wilson(x, n, z=1.959963984540054):
    if n == 0: return (None, None)
    p = x / n; d = 1 + z*z/n; c = (p + z*z/(2*n)) / d; h = z*math.sqrt(p*(1-p)/n + z*z/(4*n*n)) / d
    return (max(0.0, c-h), min(1.0, c+h))
def logpmf(k, n, p):
    return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)+k*math.log(p)+(n-k)*math.log1p(-p)
def binom_two_sided(x, n, p):
    """Exact two-sided binomial test (sum of outcomes no more likely than x), as in scipy.stats.binomtest."""
    lx = logpmf(x, n, p); tot = 0.0
    for k in range(n+1):
        lk = logpmf(k, n, p)
        if lk <= lx + 1e-7*abs(lx): tot += math.exp(lk)
    return min(1.0, tot)
def shots95(p):
    return None if not p else math.ceil(math.log(0.05) / math.log1p(-p))

rows = []
for pid in sorted(pair, key=pkey):
    c, e = pid.split("__"); J = sorted([j for j in jobs if j["pairing_id"] == pid], key=lambda j: j["slot"])
    n = sum(j["shots"] for j in J); L = sum(j["legal_count"] for j in J); O = sum(j["optimal_count"] for j in J)
    rates = [j["optimal_rate"] for j in J]; m = sum(rates)/len(rates)
    sd = math.sqrt(sum((r-m)**2 for r in rates)/(len(rates)-1))
    rng = random.Random(20261016); boots = sorted(sum(rng.choice(rates) for _ in rates)/len(rates) for _ in range(10000))
    succ = sum(j["optimal_count"] > 0 for j in J)
    R = ref[pid]; po = O/n; u = R["exact_uniform_optimal"]; ideal = R["ideal_qaoa_optimal"]
    s = sa[(c, e)]; b = br[(c, e)]
    gates = sorted(set(b["compiled_two_qubit_gates_by_version_used"].values()))
    rows.append({
        "bay": c, "encoding": ENC[e], "pairing_id": pid, "containers": inst[c]["containers"], "optimum_relocations": inst[c]["optimum"],
        "decision_qubits": pair[pid]["decision_qubits"], "compiled_2q_gates": gates[0] if len(gates) == 1 else "/".join(map(str, gates)),
        "angle_id": R["angle_id"], "prep_versions": ",".join(str(j["prep_version"]) for j in J),
        "first_submitted_utc": J[0]["submitted_utc"][:16], "last_submitted_utc": J[-1]["submitted_utc"][:16],
        "jobs": len(J), "shots": n, "qpu_charge_s": sum(j["qpu_charge_seconds"] for j in J),
        "legal_shots": L, "legal_rate": L/n, "legal_ci_low": wilson(L, n)[0], "legal_ci_high": wilson(L, n)[1],
        "optimal_shots": O, "optimal_rate": po, "optimal_ci_low": wilson(O, n)[0], "optimal_ci_high": wilson(O, n)[1],
        "optimal_given_legal": O/L if L else None,
        "job_optimal_min": min(rates), "job_optimal_max": max(rates), "job_optimal_sd": sd,
        "job_bootstrap_low": boots[249], "job_bootstrap_high": boots[9749],
        "jobs_finding_optimum": succ, "job_success_ci_low": wilson(succ, len(J))[0], "job_success_ci_high": wilson(succ, len(J))[1],
        "best_relocations": min(j["best_relocations"] for j in J if j["best_relocations"] is not None),
        "exact_uniform_legal": R["exact_uniform_legal"], "exact_uniform_optimal": u,
        "difference_vs_uniform_pp": 100*(po-u), "lift_vs_uniform": po/u,
        "binomial_p_vs_uniform_two_sided": binom_two_sided(O, n, u),
        "ideal_noiseless_legal": R["ideal_qaoa_legal"], "ideal_noiseless_optimal": ideal,
        "hardware_retention_optimal": po/ideal, "hardware_retention_legal": (L/n)/R["ideal_qaoa_legal"],
        "shots_for_95pct_one_optimum_hw": shots95(po), "shots_for_95pct_one_optimum_uniform": shots95(u),
        "sa_runs_optimal_of_5": s["runs_optimal"], "sa_candidate_optimal_fraction": s["candidate_legal_optimal_fraction"],
        "greedy_relocations": gr[c]["greedy_relocations"], "milp_optimum": mi[c]["milp_objective"], "milp_seconds": mi[c]["runtime_seconds"],
    })
# Holm adjustment over the 8 exploratory uniform comparisons
ps = sorted(range(len(rows)), key=lambda i: rows[i]["binomial_p_vs_uniform_two_sided"]); run = 0.0
for k, i in enumerate(ps):
    run = max(run, min(1.0, (len(rows)-k)*rows[i]["binomial_p_vs_uniform_two_sided"])); rows[i]["holm_adjusted_p"] = run
for r in rows:
    r["verdict_vs_uniform"] = ("above uniform" if r["holm_adjusted_p"] < 0.05 and r["lift_vs_uniform"] > 1 else
                               "below uniform" if r["holm_adjusted_p"] < 0.05 else "not distinguishable from uniform")

jobs_sorted = []
for pid in sorted(pair, key=pkey):
    c, e = pid.split("__")
    for rep, j in enumerate(sorted([j for j in jobs if j["pairing_id"] == pid], key=lambda j: j["slot"]), 1):
        jobs_sorted.append({"bay": c, "encoding": ENC[e], "repeat": rep, "planned_slot": j["slot"], "job_id": j["job_id"],
            "prep_version": j["prep_version"], "backend": j["backend"], "submitted_utc": j["submitted_utc"][:19],
            "shots": j["shots"], "legal_shots": j["legal_count"], "legal_rate": j["legal_rate"],
            "optimal_shots": j["optimal_count"], "optimal_rate": j["optimal_rate"], "found_optimum": int(j["optimal_count"] > 0),
            "best_relocations": j["best_relocations"], "gap_to_optimum": None if j["best_relocations"] is None else j["best_relocations"]-inst[c]["optimum"],
            "qpu_charge_s": j["qpu_charge_seconds"]})

pairs = []
for c in ["random-S3T4C6-21", "random-S3T4C6-24", "random-S3T4C7-32"]:
    P = next(r for r in rows if r["pairing_id"] == f"{c}__predicate"); Q = next(r for r in rows if r["pairing_id"] == f"{c}__galle")
    pairs.append({"bay": c, "predicate_qubits": P["decision_qubits"], "qubo_qubits": Q["decision_qubits"],
        "predicate_2q_gates": P["compiled_2q_gates"], "qubo_2q_gates": Q["compiled_2q_gates"],
        "predicate_optimal_rate": P["optimal_rate"], "qubo_optimal_rate": Q["optimal_rate"],
        "predicate_lift_vs_uniform": P["lift_vs_uniform"], "qubo_lift_vs_uniform": Q["lift_vs_uniform"],
        "predicate_ideal_optimal": P["ideal_noiseless_optimal"], "qubo_ideal_optimal": Q["ideal_noiseless_optimal"],
        "predicate_retention": P["hardware_retention_optimal"], "qubo_retention": Q["hardware_retention_optimal"],
        "predicate_angles": P["angle_id"], "qubo_angles": Q["angle_id"],
        "note": "Different angle policies and circuits: descriptive only, not an encoding effect"})

instances = [{"bay": c, "stacks_bottom_to_top": inst[c]["stacks_json"], "capacity": inst[c]["capacity"], "containers": inst[c]["containers"],
              "optimum_relocations": inst[c]["optimum"], "source": "published benchmark (Caserta class 3-3)" if c.startswith("data") else "project-generated random bay",
              "milp_seconds": mi[c]["runtime_seconds"], "greedy_relocations": gr[c]["greedy_relocations"]} for c in BAY_ORDER]
prep_rows = [{"bay": p["pairing_id"].split("__")[0], "encoding": ENC[p["pairing_id"].split("__")[1]], "prep_version": p["version"],
              "angle_id": p["angle_id"], "angles_gamma1_gamma2_beta1_beta2": p["theta_json"], "prepared_utc": p["prepared_utc"][:19],
              "compiled_circuit_sha256": p["isa_sha256"]} for p in sorted(preps, key=lambda p: (*pkey(p["pairing_id"]), p["version"]))]

README = [
 ("What this is", "A sorted, analysis-ready view of the completed IBM ibm_fez rCRP QAOA study (40 jobs, 80,000 shots, p=2, fixed angles, no error mitigation). Nothing was rerun on IBM."),
 ("Source", "Read-only from rCRP_IBM_Database_2026_10_16/ibm_results.sqlite and QAOA_Classical_Companion_2026_10_16_v1. The original database is unchanged."),
 ("Sort order", "Bays from smallest to largest (6 containers, then 7, then the 9-container published benchmark); Predicate before QUBO; jobs in submission order."),
 ("QUBO", "QUBO = the Galle CRP-I exact QUBO encoding (labelled 'galle' in the raw database)."),
 ("Rates", "Legal rate and optimal rate use ALL shots as the denominator. CI = Wilson 95% interval treating shots as independent (approximation)."),
 ("Uniform baseline", "exact_uniform_* = exact fraction of all 2^n bit strings that decode to a legal / optimal plan (full enumeration, no sampling)."),
 ("Ideal (noiseless)", "ideal_noiseless_* = exact p=2 QAOA probability at the same frozen angles with no noise (state-vector). Retention = hardware rate / ideal rate."),
 ("p-values", "Exact two-sided binomial test of the pooled optimal count against the exact uniform rate, Holm-adjusted over 8 pairings. Post-hoc and exploratory: assumes independent shots and ignores job-to-job drift."),
 ("Job bootstrap", "Percentile 95% interval from resampling the 5 job rates (10,000 resamples, seed 20261016). Fragile with 5 jobs."),
 ("Classical", "SA = matched-count simulated annealing (5 seeds x 2,000 candidates). Greedy and MILP are deterministic. Matching is by candidate count, not cost."),
 ("Caution", "Predicate used per-bay leave-one-out angles; QUBO used one common fresh angle vector. Encoding differences are descriptive only. No quantum advantage is claimed."),
]

def write_sheet(wb, name, data, pct=(), small=()):
    ws = wb.create_sheet(name); cols = list(data[0])
    ws.append(cols)
    for c in ws[1]: c.font = Font(bold=True, color="FFFFFF"); c.fill = PatternFill("solid", fgColor="2F4F6F"); c.alignment = Alignment(wrap_text=True, vertical="top")
    for r in data: ws.append([r[k] for k in cols])
    for i, k in enumerate(cols, 1):
        L = get_column_letter(i); ws.column_dimensions[L].width = max(10, min(34, len(k) + 2))
        fmt = "0.00%" if k in pct else ("0.0E+00" if k in small else None)
        if fmt:
            for cell in ws[L][1:]: cell.number_format = fmt
    ws.freeze_panes = "C2"; ws.auto_filter.ref = ws.dimensions
    with open(OUT / f"{name}.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(data)

wb = Workbook(); ws = wb.active; ws.title = "Read_me"
ws.append(["Item", "Explanation"]); [setattr(c, "font", Font(bold=True)) for c in ws[1]]
for a, b in README: ws.append([a, b])
ws.column_dimensions["A"].width = 20; ws.column_dimensions["B"].width = 140
pct = {k for k in rows[0] if any(t in k for t in ("rate", "ci_", "_min", "_max", "bootstrap", "uniform_legal", "uniform_optimal", "ideal_", "given_legal", "fraction", "_sd", "retention"))}
write_sheet(wb, "Summary_by_bay", rows, pct, {"binomial_p_vs_uniform_two_sided", "holm_adjusted_p"})
write_sheet(wb, "Jobs_sorted", jobs_sorted, {"legal_rate", "optimal_rate"})
write_sheet(wb, "Predicate_vs_QUBO", pairs, {k for k in pairs[0] if "rate" in k or "ideal" in k or "retention" in k})
write_sheet(wb, "Instances", instances)
write_sheet(wb, "Preparations", prep_rows)
wb.save(OUT / "rCRP_IBM_Results_Sorted.xlsx")
json.dump({"summary": rows, "predicate_vs_qubo": pairs}, open(OUT / "analysis_measures.json", "w"), indent=1)
(OUT / "README.txt").write_text("\n".join(f"{a}: {b}" for a, b in README) + "\n\nBuilt by build_sorted.py (copied here) from the read-only sources above.\n")
(OUT / "build_sorted.py").write_text(Path(__file__).read_text()); (OUT / "reference_rates.json").write_text(REF.read_text())
(OUT / "SHA256SUMS.txt").write_text("".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(OUT.iterdir()) if p.name != "SHA256SUMS.txt"))
for r in rows:
    print(f"{r['pairing_id']:32s} opt {r['optimal_rate']:.4f} uni {r['exact_uniform_optimal']:.4f} lift {r['lift_vs_uniform']:.2f} holm {r['holm_adjusted_p']:.2g} ideal {r['ideal_noiseless_optimal']:.4f} ret {r['hardware_retention_optimal']:.2f} legret {r['hardware_retention_legal']:.2f} jobs {r['jobs_finding_optimum']}/5 boot [{r['job_bootstrap_low']:.4f},{r['job_bootstrap_high']:.4f}] n95 {r['shots_for_95pct_one_optimum_hw']} vs {r['shots_for_95pct_one_optimum_uniform']} {r['verdict_vs_uniform']}")
