"""Count-only extension. Does not simulate or solve larger bays."""
import json,sys,time
from pathlib import Path
sys.dont_write_bytecode=True
from sim9_bridge import sim9
m=sim9();rows=[]
for stem in ['data3-4','data4-4','data4-5']:
    for index in range(1,4):
        name=f'{stem}-{index}';item=m.catalog_item(name)
        for method in ['predicate','galle']:
            start=time.perf_counter()
            p=m.Problem(item['stacks_bottom_to_top'],item['capacity'],method,presolve='standard')
            g=m.logical_two_qubit_gates(p,2)
            rows.append(dict(case=name,containers=item['containers'],stacks=item['stacks_bottom_to_top'],capacity=item['capacity'],method=method,presolve='standard',depth=2,resources=g,seconds=time.perf_counter()-start,scope='logical construction estimate; no IBM routing, no solution samples'))
            print(name,method,g,flush=True)
out=Path(sys.argv[1]);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2))
