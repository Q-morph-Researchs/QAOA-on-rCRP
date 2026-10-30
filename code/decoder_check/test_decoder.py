import copy,json,unittest,ast
from pathlib import Path
from independent_decoder import decode,replay,values
HERE=Path(__file__).resolve().parent
C=json.loads((HERE/'ENCODING_CONTRACT.json').read_text())
class DecoderTests(unittest.TestCase):
    def setUp(self):
        self.c=C['random-S3T4C6-21__predicate']; self.state=8; self.o=decode(self.c,self.state)
    def test_known_feasible(self):
        self.assertTrue(self.o['legal']);self.assertEqual(self.o['relocations'],1)
    def test_domain_rejection(self):
        for state in (-1,256,1.5):
            with self.assertRaises(ValueError):decode(self.c,state)
    def test_initial_configuration_corruption(self):
        c=copy.deepcopy(self.c)
        next(v for v in c['variables'] if v['key']==[1,7,1])['literal']={'constant':0}
        self.assertFalse(decode(c,self.state)['legal'])
    def test_non_top_replay_rejection(self):
        self.assertEqual(replay(self.c['stacks'],4,[{'type':'retrieve','container':2,'source':3}]),(False,None))
    def test_wrong_retrieval_order_rejected(self):
        self.assertEqual(replay(self.c['stacks'],4,[{'type':'retrieve','container':5,'source':3}]),(False,None))
    def test_relocation_to_same_stack_rejected(self):
        plan=copy.deepcopy(self.o['moves']);mv=next(m for m in plan if m['type']=='relocate');mv['destination']=mv['source']
        self.assertFalse(replay(self.c['stacks'],4,plan)[0])
    def test_incomplete_plan_rejected(self):
        self.assertFalse(replay(self.c['stacks'],4,self.o['moves'][:-1])[0])
    def test_slack_does_not_change_physical_decode(self):
        c=C['random-S3T4C6-21__galle'];mask=(1<<c['physical_bits'])-1
        for state in range(1<<c['n']):self.assertEqual(decode(c,state),decode(c,state&mask))
    def test_replay_all_first_legal(self):
        for c in C.values():
            o=next(decode(c,k) for k in range(1<<c['n']) if decode(c,k)['legal'])
            self.assertEqual(replay(c['stacks'],c['capacity'],o['moves']),(True,o['relocations']))
    def test_no_imports_or_original_decoder_calls(self):
        tree=ast.parse((HERE/'independent_decoder.py').read_text())
        self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(tree)))
        forbidden={'recover','outcome','decode_galle','stage_config','check','encoding'}
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in forbidden for n in ast.walk(tree)))
if __name__=='__main__':unittest.main(verbosity=2)
