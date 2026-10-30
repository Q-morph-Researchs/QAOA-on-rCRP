"""Build a fresh database and CSV/Markdown analysis from saved evidence."""
import argparse,csv,json,math,shutil,sqlite3,statistics,hashlib
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def dump(p,o): p.write_text(json.dumps(o,indent=2,allow_nan=False))
def csvwrite(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h,c+h
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--results',default=str(ROOT/'results'));a=ap.parse_args()
    results=Path(a.results).resolve()
    for rel,h in json.loads((ROOT/'ADDITIONAL_INPUT_HASHES.json').read_text()).items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==h, 'Changed analysis input: '+rel
    out=Path(a.output).resolve();out.mkdir(parents=True,exist_ok=True)
    db=out/'combined_results.sqlite'
    if db.exists():raise SystemExit('Refusing to overwrite database: use a fresh output directory')
    shutil.copy2(ROOT/'inputs/ibm_results.sqlite',db)
    con=sqlite3.connect(db);con.execute('PRAGMA foreign_keys=ON')
    con.executescript('''
CREATE TABLE simulation_runs(run_id TEXT PRIMARY KEY,job_id TEXT REFERENCES jobs(job_id),pairing_id TEXT,condition TEXT,seed INTEGER,prep_version INTEGER,shots INTEGER,legal_count INTEGER,optimal_count INTEGER,wall_seconds REAL);
CREATE TABLE simulation_shots(run_id TEXT REFERENCES simulation_runs(run_id),shot_index INTEGER,state INTEGER,PRIMARY KEY(run_id,shot_index));
CREATE TABLE exact_simulation_reference(pairing_id TEXT,state INTEGER,ideal_probability REAL,legal INTEGER,optimal INTEGER,relocations INTEGER,scaled_energy REAL,PRIMARY KEY(pairing_id,state));
CREATE TABLE simulation_preparation(pairing_id TEXT,version INTEGER,audit_json TEXT,PRIMARY KEY(pairing_id,version));
''')
    rows=[];records=sorted((results/'jobs').glob('*/result.json'))
    assert len(records)==40
    mapping={ (case,enc):pid for pid,case,enc in con.execute('SELECT pairing_id,case_id,encoding FROM pairings')}
    for path in records:
        r=json.loads(path.read_text());pid=mapping[r['case'],r['method']]
        for cond in ['hardware','ideal_sampled','snapshot_noise']:
            s=r['scores'][cond];row=dict(slot=r['slot'],job_id=r['job_id'],pairing=pid,condition=cond,prep_version=r['prep_version'],shots=s['shots'],legal_count=s['legal_count'],optimal_count=s['optimal_count'],legal_rate=s['legal_count']/s['shots'],optimal_rate=s['optimal_count']/s['shots'])
            rows.append(row)
            if cond=='hardware':continue
            label='ideal' if cond=='ideal_sampled' else 'noisy'
            seed=r['ideal_seed'] if cond=='ideal_sampled' else r['noise_seed']
            rid=f"{r['slot']:02d}_{cond}"
            con.execute('INSERT INTO simulation_runs VALUES(?,?,?,?,?,?,?,?,?,?)',(rid,r['job_id'],pid,cond,seed,r['prep_version'],s['shots'],s['legal_count'],s['optimal_count'],r['noisy_wall_seconds'] if cond=='snapshot_noise' else None))
            states=np.load(path.parent/f'{label}_states.npy')
            con.executemany('INSERT INTO simulation_shots VALUES(?,?,?)',((rid,i,int(v)) for i,v in enumerate(states)))
    aggregates=[];audits=[]
    for path in sorted((results/'pairings').glob('*/exact.json')):
        e=json.loads(path.read_text());pid=mapping[e['case'],e['method']];space=np.load(path.parent/'state_space.npz')
        con.executemany('INSERT INTO exact_simulation_reference VALUES(?,?,?,?,?,?,?)',((pid,i,float(p),int(space['legal'][i]),int(space['optimal'][i]),int(space['relocations'][i]) if space['legal'][i] else None,float(space['energy_scaled'][i])) for i,p in enumerate(space['ideal'])))
        ag=dict(pairing=pid,case=e['case'],encoding=e['method'],qubits=e['n'],state_count=e['states'],uniform_legal=e['uniform_legal'],uniform_optimal=e['uniform_optimal'],ideal_exact_legal=e['ideal_legal'],ideal_exact_optimal=e['ideal_optimal'])
        for cond in ['hardware','ideal_sampled','snapshot_noise']:
            rr=[r for r in rows if r['pairing']==pid and r['condition']==cond];assert len(rr)==5
            for metric in ['legal','optimal']:
                k=sum(r[metric+'_count'] for r in rr);n=sum(r['shots'] for r in rr);p=k/n;lo,hi=wilson(k,n)
                prefix=f'{cond}_{metric}'
                ag.update({prefix:p,prefix+'_count':k,prefix+'_wilson_low':lo,prefix+'_wilson_high':hi,prefix+'_job_sd':statistics.stdev(r[metric+'_rate'] for r in rr),prefix+'_job_min':min(r[metric+'_rate'] for r in rr),prefix+'_job_max':max(r[metric+'_rate'] for r in rr)})
            ag[cond+'_jobs_with_optimum']=sum(r['optimal_count']>0 for r in rr)
        ag['hardware_minus_ideal_optimal_pp']=100*(ag['hardware_optimal']-e['ideal_optimal'])
        ag['noise_minus_hardware_optimal_pp']=100*(ag['snapshot_noise_optimal']-ag['hardware_optimal'])
        ag['hardware_uniform_optimal_ratio']=ag['hardware_optimal']/e['uniform_optimal']
        ag['hardware_uniform_legal_ratio']=ag['hardware_legal']/e['uniform_legal']
        aggregates.append(ag)
    for p in sorted((results/'preparations').glob('*/v*/audit.json')):
        item=p.parent.parent.name;v=int(p.parent.name[1:]);r=json.loads(p.read_text());case,method=item.split('__');pid=mapping[case,method]
        con.execute('INSERT INTO simulation_preparation VALUES(?,?,?)',(pid,v,json.dumps(r)))
        audits.append(dict(pairing=pid,version=v,qubits=r['decision_qubits'],active_qubits=r['active_qubits'],two_qubit_gates=r['compiled_two_qubit_gates'],depth=r['compiled_depth'],snapshot_utc=r['snapshot_captured_utc'],max_ideal_error=r['max_ideal_error'],isa_sha256=r['isa_sha256']))
    con.commit();assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok';assert con.execute('PRAGMA foreign_key_check').fetchall()==[]
    counts={t:con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['jobs','shots','simulation_runs','simulation_shots','exact_simulation_reference','simulation_preparation']}
    dump(out/'VALIDATION.json',dict(sqlite_integrity='ok',foreign_keys='pass',counts=counts))
    csvwrite(out/'comparison.csv',aggregates);csvwrite(out/'all_job_rates.csv',rows);csvwrite(out/'circuit_resources.csv',audits)
    dump(out/'comparison.json',aggregates)
    # Export new tables for tools that do not read SQLite.
    for table in ['simulation_runs','simulation_preparation']:
        cur=con.execute(f'SELECT * FROM {table}');names=[d[0] for d in cur.description];csvwrite(out/f'{table}.csv',[dict(zip(names,r)) for r in cur])
    con.close()
    table=['| Bay / encoding | Ideal optimal % | Noise-model optimal % | IBM optimal % | Exact uniform optimal % |','|---|---:|---:|---:|---:|']
    for r in aggregates:table.append(f"| {r['case']} / {r['encoding']} | {100*r['ideal_exact_optimal']:.3f} | {100*r['snapshot_noise_optimal']:.3f} | {100*r['hardware_optimal']:.3f} | {100*r['uniform_optimal']:.3f} |")
    text='''# Simulation companion: results and interpretation

This is a supplementary study designed after the IBM results were known. The protocol was frozen before its simulated samples were generated. Original hardware files, angles and classical results were not changed. No IBM service was contacted.

## What was collected and why

Eight bay/encoding combinations on five bays, matched to all 40 IBM jobs. Every simulation used the saved angles and the actual logical/compiled circuit for that job: slots 1-26 v1, slot 27 v2, slots 28-40 v3. We enumerated each encoding's complete bitstring space and independently replayed every accepted move plan. Exact ideal probabilities distinguish the algorithm's ideal distribution from sampling variation. Independent 2,000-shot ideal and noisy samples match each hardware job's shot count. This count match does not equate computational costs.

Ideal simulation is checked three ways: an independent QAOA vector calculation, the saved logical circuit, and the saved compiled circuit after removing idle physical qubits. Compaction preserves physical-to-classical measurement order; the noise model is remapped to those same active qubits. Calibration and model-input hashes are preserved.

Classical presolve and feasible-witness penalty bounds in the original encoding remain in place. Exact state enumeration is for simulation and scoring validation, not an answer fed into hardware or used to choose a measured result. The direct QAOA calculation applies phase and mixer unitaries to the complete statevector, using normalized energy and the frozen angles. It does not replace the circuit sampler with an optimal-plan lookup.

The approximate noise model uses Aer gate-error depolarization and asymmetric readout errors from each saved preparation-time IBM snapshot. Explicit thermal relaxation is disabled: the snapshots lack frequencies expected by the full Aer constructor. Gate error can already reflect relaxation contributions; this model does not add a separate T1/T2 process. It also omits coherent error, crosstalk, leakage, idle relaxation and time-dependent drift. It is not the exact noise experienced by IBM jobs. The model parameters were not fitted to the hardware outcomes.

## Optimal-plan samples

Denominator: all shots, including illegal outputs. Ideal and uniform columns are exact probabilities; noisy and hardware columns are measured fractions from 10,000 samples per pairing. Legal means the decoded physical plan obeys rCRP rules. In the QUBO encoding, this can include bitstrings whose auxiliary slack bits are inconsistent. An optimal decoded plan is therefore not the same event as a minimum-energy bitstring. This scoring matches the hardware study.

'''+ '\n'.join(table)+'''

## Quantitative analysis

`comparison.csv` includes legal and optimal probabilities, counts, job success counts, per-job standard deviation/range, and 95% Wilson intervals. Hardware intervals are conditional shot-level descriptions under an independent-identically-distributed approximation; they do not account for calibration drift or correlations. Five hardware repetitions are not five independent devices or bays. The noisy intervals describe Monte Carlo variation within a fixed approximate model; they do not describe uncertainty in the model itself.

The hardware-minus-ideal difference in percentage points measures observed degradation relative to the frozen ideal circuit. It does not identify which error mechanism caused it. The noisy-minus-hardware difference measures model discrepancy. Ratios to exact uniform sampling measure enrichment among encoded bitstrings, not speedup over classical algorithms. Exact uniform values can differ from the previously recorded finite random samples; those historical results remain unchanged in the original tables.

Do not interpret total variation between finite histograms as noise alone: finite sample error contributes substantially in the larger spaces. No first-hit timing is inferred from histograms. No optimality certificate is supplied by QAOA; optimality labels come from the existing exact classical verification and are used only in scoring.

## Limits of the conclusions

The outcomes support a small-instance, fixed-angle hardware comparison. Hardware sampling of some optimal plans is not evidence of quantum advantage. Classical companion results remain: greedy optimal on five of five bays; exact solvers certify their optima; SA optimal in 39 of 40 runs. QAOA hardware found an optimum in 39 of 40 jobs. SA evaluations and hardware shots differ in cost and dependence, so equal counts do not establish equal work.

QUBO and predicate were calibrated differently, and hardware groups ran sequentially across multiple days/preparations. These differences prevent attributing all outcome differences solely to the encoding. Noise simulation helps assess a possible mechanism, but does not eliminate those confounds. Larger-bay logical resource estimates are construction-specific counts, not solved large-instance experiments or a universal maximum container count. No newly routed large circuits, hardware jobs, angle retuning or noise-fitting experiments were performed.

## Sources and reproducibility

Noise model API: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.noise.NoiseModel.html
Device-noise approximation: https://qiskit.github.io/qiskit-aer/tutorials/2_device_noise_simulation.html
Simulator: https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html

Use the paired evidence ZIP, its protocol, input hashes, scripts, saved state arrays, per-job seeds, snapshots and validation logs. `combined_results.sqlite` retains the prior hardware tables and adds explicitly named simulation tables. The `exact_simulation_reference` table covers the full encoding space; illegal relocations are SQL NULL. Evidence NPZ files use -1 as the documented illegal-relocation sentinel. The canonical old database is copied unchanged into evidence inputs; its rows are not overwritten.
'''
    (out/'METHODS_RESULTS_ANALYSIS.md').write_text(text)
    print(json.dumps(counts,indent=2));print('\n'.join(table))
if __name__=='__main__':main()
