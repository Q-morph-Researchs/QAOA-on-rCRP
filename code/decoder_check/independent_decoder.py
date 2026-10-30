"""Pure standard-library decoder: replay from initial bay, never reconstruct by sorting.

Shared boundary is explicit JSON bit-to-variable literal contract. This module
imports no quantum code, MILP rows, companion decoder, or known optimum.
"""

def values(contract,state):
    if not isinstance(state,int) or state<0 or state >= 1 << contract['n']:
        raise ValueError('State outside measured-register domain')
    result={}
    for entry in contract['variables']:
        literal=entry['literal']
        result[tuple(entry['key'])]=int(literal['constant']) if 'constant' in literal else ((state >> literal['bit']) & 1)^int(literal['complement'])
    return result


def decode(contract,state):
    x=values(contract,state)
    C,S,N=contract['C'],contract['S'],contract['N']; cap=contract['capacity']
    bay=[list(s) for s in contract['stacks']]; moves=[]; relocations=0
    def reject(reason):return {'legal':False,'reason':reason}
    # At each stage compute relations FROM the actual physical bay. Never infer
    # the vertical ordering by ranking, sorting, or a borrowed recovery routine.
    for target in range(1,N+1):
        location={c:(s,h) for s,stack in enumerate(bay) for h,c in enumerate(stack)}
        if sorted(location)!=list(range(target,C+1)) or any(len(s)>cap for s in bay):
            return reject('physical stage domain')
        for d in range(target,C+1):
            sd,hd=location[d]
            for c in range(target,C+S+1):
                expected=int(c-C-1==sd) if c>C else int(location[c][0]==sd and location[c][1]<hd)
                if x[target,c,d]!=expected:return reject('assignment differs from replayed stage')
        if target==N:break
        source=location[target][0]
        while bay[source][-1]!=target:
            c=bay[source][-1]
            chosen=[s for s in range(S) if x[target+1,C+s+1,c]]
            if len(chosen)!=1:return reject('destination not unique')
            dest=chosen[0]
            if dest==source or len(bay[dest])>=cap:return reject('illegal restricted destination')
            bay[dest].append(bay[source].pop()); relocations+=1
            moves.append({'type':'relocate','container':c,'source':source+1,'destination':dest+1})
        bay[source].pop();moves.append({'type':'retrieve','container':target,'source':source+1})
    # Terminal flags are one-sided constraints b[d]>=blocking(d), not equality.
    # A physically legal plan with an unnecessary b=1 remains feasible.
    for stack in bay:
        for h,c in enumerate(stack):
            if c>N and any(d<c for d in stack[:h]) and x['b',c]!=1:
                return reject('terminal blocking flag understates cost')
    for target in range(N,C+1):
        source=next(s for s,stack in enumerate(bay) if target in stack)
        while bay[source][-1]!=target:
            empty=[s for s,stack in enumerate(bay) if not stack]
            if not empty:return reject('terminal completion has no empty stack')
            dest=empty[0];c=bay[source].pop();bay[dest].append(c);relocations+=1
            moves.append({'type':'relocate','container':c,'source':source+1,'destination':dest+1})
        bay[source].pop();moves.append({'type':'retrieve','container':target,'source':source+1})
    return {'legal':True,'relocations':relocations,'moves':moves,'model_objective':sum(coef*x[tuple(key)] for key,coef in contract['model_objective'])}


def replay(stacks,capacity,moves):
    """Separate plan checker, no encoding variables."""
    bay=[list(s) for s in stacks]; next_target=1; count=0
    for move in moves:
        s=move['source']-1;c=move['container']
        if not 0<=s<len(bay) or not bay[s] or bay[s][-1]!=c:return False,None
        if move['type']=='retrieve':
            if c!=next_target:return False,None
            bay[s].pop();next_target+=1
        elif move['type']=='relocate':
            d=move['destination']-1
            if not 0<=d<len(bay) or d==s or len(bay[d])>=capacity or next_target not in bay[s] or c==next_target:return False,None
            bay[d].append(bay[s].pop());count+=1
        else:return False,None
    return not any(bay),count
