import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from axm_stickers import Registry,instance
from axm_stickers.assembly import save_assembly,expand,library_bundle,import_library
from axm_stickers.placement import identity


def definition():
    body=b'original editable creative part';sha=hashlib.sha256(body).hexdigest()
    return {'schema':'axm.sticker/v1','id':'part','version':1,'name':'Original part','tags':['salvage'],
            'origin':{'author':'AXM','license':'CC0-1.0','source':'Original protocol fixture'},
            'adapter':'example.rigid/v1','attachment':{'space':'3d','socket':'mount','anchor':identity()},
            'recipe':{'size':1.0},'parameters':{'size':{'path':['size'],'type':'number','min':.1,'max':10,'default':1.0}},
            'assets':{'source':sha}}, {sha:body}

class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.r=Registry(self.root/'registry.sqlite');self.addCleanup(self.r.db.close)
        self.d,assets=definition();self.r.register(self.d,assets)
    def test_immutable_source_and_independent_instances(self):
        a=instance(self.d,'a',overrides={'size':2.0});b=instance(self.d,'b')
        self.assertNotEqual(a['overrides'],b['overrides'])
        changed=copy.deepcopy(self.d);changed['name']='Changed'
        with self.assertRaises(ValueError):self.r.register(changed)
        self.assertEqual(self.r.get('part',1),self.d)
    def test_atomic_batch_and_indexed_shared_assets(self):
        entries=[]
        for i in range(500):
            d=copy.deepcopy(self.d);d['id']='part-'+str(i);entries.append(d)
        self.r.register_many(entries)
        self.assertEqual(self.r.db.execute('SELECT count(*) FROM assets').fetchone()[0],1)
        self.assertEqual(len(self.r.search(tag='salvage',limit=100)['entries']),100)
        new=copy.deepcopy(self.d);new['id']='new';bad=copy.deepcopy(self.d);bad['name']='conflict'
        with self.assertRaises(ValueError):self.r.register_many([new,bad])
        with self.assertRaises(ValueError):self.r.get('new',1)
    def test_nested_saved_group_and_exact_portable_closure(self):
        def group(id,d):
            children=[{'instance':instance(d,'one'),'target':{'space':'3d','socket':'mount','frame':identity()},'motion':None,'clip':None}]
            return save_assembly(self.r,id=id,name=id,origin=d['origin'],children=children)
        first=group('first',self.d);second=group('second',first)
        self.assertEqual(len(expand(self.r,second)),3)
        bundle=library_bundle(self.r,'second',1)
        with Registry(self.root/'other.sqlite') as other:
            import_library(other,bundle)
            self.assertEqual(library_bundle(other,'second',1),bundle)
        bad=copy.deepcopy(bundle);bad['assets'][next(iter(bad['assets']))]='YmFk'
        with Registry(self.root/'empty.sqlite') as other:
            with self.assertRaises(ValueError):import_library(other,bad)
            self.assertEqual(other.search()['entries'],[])
    def test_shipped_rivetwing_library_retains_full_source_closure(self):
        bundle=json.loads((Path(__file__).resolve().parents[1]/'examples/rivetwing-library.json').read_text())
        with Registry(self.root/'rivetwing.sqlite') as other:
            import_library(other,bundle)
            records=expand(other,other.get('rivetwing',1))
            self.assertEqual(len(records),277)
            self.assertEqual(len({r['definition']['assets'].get('model') for r in records if r['definition']['assets']}),15)
            self.assertEqual(library_bundle(other,'rivetwing',1),bundle)

    def test_cli_works_outside_source_and_has_no_uc_dependency(self):
        request=self.root/'request.json';request.write_text(json.dumps({'operation':'search','tag':'salvage'}))
        run=subprocess.run([sys.executable,'-m','axm_stickers',str(self.root/'registry.sqlite'),str(request)],cwd=self.root,capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['entries'][0]['id'],'part')
        self.assertFalse(any(k.startswith('axm_uc') for k in sys.modules))

if __name__=='__main__':unittest.main()
