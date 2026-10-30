"""Read-only import of original IBM study into a new SQLite analysis database."""
import sys,json,sqlite3,csv,hashlib,math,statistics,zipfile
from pathlib import Path
from collections import Counter
import numpy as np
sys.dont_write_bytecode=True
R=Path('/Users/radin/Downloads');S=R/'QAOA_Sim9_2_IBM_Repaired_2026_10_12/studies/ibm_live_guide_1'
C=R/'QAOA_Classical_Companion_2026_10_16_v1'
O=R/'rCRP_IBM_Database_2026_10_16';O.mkdir(exist_ok=True)
sys.path.insert(0,str(C/'code'))
from sim9_bridge import Pairing
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n;mid=(p+z*z/(2*n))/den;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return max(0,mid-half),min(1,mid+half)
db=O/'ibm_results.sqlite'
if db.exists():raise SystemExit('Output database exists; choose a new output folder to preserve evidence.')
con=sqlite3.connect(db);con.execute('PRAGMA foreign_keys=ON')
con.executescript('''
CREATE TABLE instances(case_id TEXT PRIMARY KEY, stacks_json TEXT NOT NULL, capacity INTEGER NOT NULL, containers INTEGER NOT NULL, optimum INTEGER NOT NULL, provenance TEXT);
CREATE TABLE pairings(pairing_id TEXT PRIMARY KEY,case_id TEXT REFERENCES instances,encoding TEXT,decision_qubits INTEGER);
CREATE TABLE preparations(pairing_id TEXT REFERENCES pairings,version INTEGER,theta_json TEXT,angle_id TEXT,prepared_utc TEXT,isa_sha256 TEXT,prep_json TEXT,PRIMARY KEY(pairing_id,version));
CREATE TABLE jobs(job_id TEXT PRIMARY KEY,slot INTEGER UNIQUE,attempt_id TEXT UNIQUE,pairing_id TEXT,prep_version INTEGER,backend TEXT,status TEXT,submitted_utc TEXT,collected_utc TEXT,shots INTEGER,legal_count INTEGER,optimal_count INTEGER,best_relocations INTEGER,qpu_charge_seconds REAL,registry_sha256 TEXT,FOREIGN KEY(pairing_id,prep_version) REFERENCES preparations(pairing_id,version));
CREATE TABLE outcomes(pairing_id TEXT REFERENCES pairings,state INTEGER,bitstring TEXT,legal INTEGER,optimal INTEGER,relocations INTEGER,energy REAL,moves_json TEXT,PRIMARY KEY(pairing_id,state));
CREATE TABLE shots(job_id TEXT REFERENCES jobs,shot_index INTEGER,state INTEGER,PRIMARY KEY(job_id,shot_index));
CREATE TABLE histograms(job_id TEXT REFERENCES jobs,state INTEGER,count INTEGER,PRIMARY KEY(job_id,state));
CREATE TABLE source_files(relative_path TEXT PRIMARY KEY,sha256 TEXT,size_bytes INTEGER);
CREATE TABLE summary_metrics(pairing_id TEXT PRIMARY KEY REFERENCES pairings,metrics_json TEXT);
CREATE VIEW shot_outcomes AS SELECT s.job_id,s.shot_index,s.state,j.pairing_id,o.legal,o.optimal,o.relocations FROM shots s JOIN jobs j USING(job_id) JOIN outcomes o ON j.pairing_id=o.pairing_id AND s.state=o.state;
CREATE VIEW job_rates AS SELECT *,CAST(legal_count AS REAL)/shots AS legal_rate,CAST(optimal_count AS REAL)/shots AS optimal_rate FROM jobs;
''')
bays=read(C/'inputs/bays_and_provenance.json')['bays'];pairs={};configs={}
for case,b in bays.items():con.execute('INSERT INTO instances VALUES(?,?,?,?,?,?)',(case,json.dumps(b['stacks']),b['capacity'],sum(map(len,b['stacks'])),b['claimed_optimum'],b['benchmark_provenance']))
summary=read(S/'summary.json');checks=[]
for r in summary['rows']:
    key=r['case']+'__'+r['method'];obj=Pairing(r['case'],r['method']);pairs[key]=obj;configs[key]=r
    con.execute('INSERT INTO pairings VALUES(?,?,?,?)',(key,r['case'],r['method'],obj.n))
for f in sorted((S/'registry').glob('*.json')):
    r=read(f);key=r['case']+'__'+r['method'];obj=pairs[key];v=r['prep']['version'];prep=S/'prep'/key/f'v{v}'/'prep.json'
    con.execute('INSERT OR IGNORE INTO preparations VALUES(?,?,?,?,?,?,?)',(key,v,json.dumps(r['prep']['theta']),r['prep']['angle_id'],r['prep']['prepared_utc'],r['prep']['isa_sha256'],prep.read_text()))
    assert sha(prep.parent/'isa.qpy')==r['prep']['isa_sha256']
    result=S/'results'/r['attempt_id'];states=np.load(result/'states.npy',allow_pickle=False);raw=read(result/'raw_result.json')
    assert sha(result/'states.npy')==r['results']['states_sha256']
    hist=Counter(map(int,states));assert {int(k,2):v for k,v in raw['counts'].items()}==dict(hist)
    legal=optimal=0;best=None;opt=bays[r['case']]['claimed_optimum']
    for state,n in hist.items():
        o=obj.outcome(state);assert o['legal_agrees_with_own_rows'] and o['relocations_agree_with_own_replay']
        valid=o['sim9_legal'];rel=o['sim9_relocations'] if valid else None;hit=bool(valid and rel==opt)
        legal+=n*valid;optimal+=n*hit
        if valid:best=rel if best is None else min(best,rel)
        con.execute('INSERT OR IGNORE INTO outcomes VALUES(?,?,?,?,?,?,?,?)',(key,state,format(state,f'0{obj.n}b'),int(valid),int(hit),rel,o['energy'],json.dumps(o.get('moves'))))
    score=r['results']['score'];assert legal==score['accepted_count'] and optimal==score['replay_optimal_count']
    con.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(r['job_id'],int(r['slot_id'].split('_')[0]),r['attempt_id'],key,v,r['backend'],r['state'],r['created_utc'],r['results']['saved_utc'],len(states),legal,optimal,best,r['accounting']['seconds'],sha(f)))
    con.executemany('INSERT INTO shots VALUES(?,?,?)',[(r['job_id'],i,int(x)) for i,x in enumerate(states)])
    con.executemany('INSERT INTO histograms VALUES(?,?,?)',[(r['job_id'],x,n) for x,n in hist.items()])
    print('Imported',r['slot_id'],flush=True)
for f in S.rglob('*'):
    if f.is_file() and f.name not in ['.DS_Store','study.lock']:con.execute('INSERT INTO source_files VALUES(?,?,?)',(str(f.relative_to(S)),sha(f),f.stat().st_size))
metrics=[]
for key,r in configs.items():
    js=con.execute('SELECT shots,legal_count,optimal_count,best_relocations FROM jobs WHERE pairing_id=? ORDER BY slot',(key,)).fetchall();N=sum(x[0] for x in js);L=sum(x[1] for x in js);K=sum(x[2] for x in js)
    assert L/N==r['accepted_rate'] and K/N==r['replay_optimal_rate']
    rates=[x[2]/x[0] for x in js];success=sum(x[2]>0 for x in js)
    # New post-hoc exploratory bootstrap: entire jobs, not individual shots. Only five jobs: weak uncertainty estimate.
    rng=np.random.default_rng(20261016);boot=np.mean(rng.choice(rates,size=(10000,5),replace=True),axis=1)
    m=dict(pairing_id=key,jobs=5,shots=N,legal_count=L,optimal_count=K,legal_rate=L/N,optimal_rate=K/N,optimal_given_legal=K/L if L else None,optimal_ci95_wilson=wilson(K,N),successful_jobs=success,success_rate=success/5,success_ci95_wilson=wilson(success,5),optimal_job_sd=statistics.stdev(rates),optimal_job_min=min(rates),optimal_job_max=max(rates),exploratory_job_bootstrap_ci95=list(np.quantile(boot,[.025,.975])),matched_uniform_optimal_rate=r['matched_uniform_optimal'],optimal_lift_vs_uniform=(K/N)/r['matched_uniform_optimal'] if r['matched_uniform_optimal'] else None,optimal_difference_percentage_points=100*(K/N-r['matched_uniform_optimal']),best_relocations=min(x[3] for x in js if x[3] is not None))
    metrics.append(m);con.execute('INSERT INTO summary_metrics VALUES(?,?)',(key,json.dumps(m)))
assert con.execute('SELECT COUNT(*) FROM shots').fetchone()[0]==80000
assert con.execute('SELECT SUM(qpu_charge_seconds) FROM jobs').fetchone()[0]==120
assert not con.execute('PRAGMA foreign_key_check').fetchall()
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
con.commit()
for table in ['instances','pairings','preparations','jobs','outcomes','histograms','job_rates']:
    cur=con.execute('SELECT * FROM '+table)
    with (O/(table+'.csv')).open('w',newline='') as f:
        w=csv.writer(f);w.writerow([x[0] for x in cur.description]);w.writerows(cur)
with (O/'analysis_summary.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(metrics[0]));w.writeheader();w.writerows(metrics)
(O/'analysis_summary.json').write_text(json.dumps(metrics,indent=2))
(O/'VALIDATION.json').write_text(json.dumps({'jobs':40,'shots':80000,'pairings':8,'instances':5,'histograms_equal_saved_shots':True,'all_decoded_counts_equal_registry_and_summary':True,'foreign_keys':'pass','sqlite_integrity':'ok','source_files_unchanged_on_import':True,'bootstrapping':'post-hoc; seed 20261016; 10000 job-resamples; five jobs/group; exploratory only'},indent=2))
con.close()
print('DATABASE COMPLETE',db)
