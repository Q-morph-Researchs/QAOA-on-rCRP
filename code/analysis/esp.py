import json,sys,glob,math
from qiskit import qpy
R=sys.argv[1]
out={}
for prep in sorted(glob.glob(R+'/simulation/inputs/prep/*/v*/')):
    snap=json.load(open(prep+'backend_snapshot.json'))['properties']
    ge={}
    for gte in snap['gates']:
        e=[p['value'] for p in gte['parameters'] if p['name']=='gate_error']
        if e: ge[(gte['gate'],tuple(gte['qubits']))]=e[0]
    ro={i:[p['value'] for p in q if p['name']=='readout_error'][0] for i,q in enumerate(snap['qubits'])}
    with open(prep+'isa.qpy','rb') as f: qc=qpy.load(f)[0]
    logp=0; cnt={}; miss=set()
    for ins in qc.data:
        n=ins.operation.name; qs=tuple(qc.find_bit(q).index for q in ins.qubits)
        cnt[n]=cnt.get(n,0)+1
        if n in ('rz','barrier','delay'): continue
        if n=='measure': e=ro[qs[0]]
        else:
            e=ge.get((n,qs)) if (n,qs) in ge else ge.get((n,qs[::-1]))
            if e is None: miss.add(n); continue
        logp+=math.log(1-e)
    key=prep.split('/prep/')[1].strip('/')
    out[key]=math.exp(logp)
    print(key,'ESP=%.3f'%math.exp(logp),cnt,'missing',miss)
json.dump(out,open(sys.argv[2],'w'),indent=1)
