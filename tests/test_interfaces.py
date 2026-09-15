import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

from axm_stickers import (Registry, assembly_target, interface_profile, instance,
                          match_interfaces, mate_frame, validate_profile,
                          validate_profile_library)
from axm_stickers.assembly import expand, import_library, save_assembly
from axm_stickers.interfaces import PROFILE_LIBRARY
from axm_stickers.placement import identity

ROOT=Path(__file__).resolve().parents[1]

def load_tool(name):
    path=ROOT/'tools'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def definition(id):
    return {'schema':'axm.sticker/v1','id':id,'version':1,'name':id,'tags':[],
            'origin':{'author':'AXM','license':'CC0-1.0','source':'Interface fixture'},
            'adapter':'example.rigid/v1',
            'attachment':{'space':'3d','socket':'mount','anchor':identity()},
            'recipe':{},'assets':{},'parameters':{}}


def port(id,interface,role,accepts,x):
    frame=identity(); frame[3]=x
    return {'id':id,'interface':interface,'role':role,'accepts':accepts,'frame':frame}


class InterfaceProfileTests(unittest.TestCase):
    def test_profile_is_exact_pin_companion_with_multiple_named_ports(self):
        d=definition('beam')
        profile=interface_profile(d,[
            port('left','structure','structure',['structure','brace'],-.75),
            port('right','structure','structure',['structure','brace'],.75)])
        self.assertEqual([p['id'] for p in profile['ports']],['left','right'])
        self.assertEqual(validate_profile(profile,d),profile)
        changed=copy.deepcopy(d);changed['name']='changed'
        with self.assertRaisesRegex(ValueError,'exact sticker'):
            validate_profile(profile,changed)
        duplicate=copy.deepcopy(profile);duplicate['ports'][1]['id']='left'
        with self.assertRaisesRegex(ValueError,'unique'):
            validate_profile(duplicate)

    def test_interface_and_mutual_roles_are_both_required(self):
        beam=interface_profile(definition('beam'),[
            port('right','structure','structure',['brace'],.75)])
        brace=interface_profile(definition('brace'),[
            port('left','structure','brace',['structure'],-.4)])
        match=match_interfaces(beam,'right',brace,'left')
        self.assertEqual(match['interface'],'structure')
        wrong_interface=copy.deepcopy(brace);wrong_interface['ports'][0]['interface']='axle'
        with self.assertRaisesRegex(ValueError,'different interfaces'):
            match_interfaces(beam,'right',wrong_interface,'left')
        one_way=copy.deepcopy(brace);one_way['ports'][0]['accepts']=['brace']
        with self.assertRaisesRegex(ValueError,'mutually accept'):
            match_interfaces(beam,'right',one_way,'left')

    def test_named_frames_author_an_ordinary_v1_assembly_target(self):
        host=definition('beam');child=definition('brace')
        hp=interface_profile(host,[port('right','structure','structure',['brace'],.75)])
        cp=interface_profile(child,[port('left','structure','brace',['structure'],-.4)])
        frame=mate_frame(hp,'right',cp,'left')
        self.assertAlmostEqual(frame[3],1.15)
        world=identity();world[3]=10
        self.assertAlmostEqual(mate_frame(hp,'right',cp,'left',host_frame=world)[3],11.15)
        target=assembly_target(host,hp,'right',child,cp,'left')
        self.assertEqual(target['space'],'3d');self.assertEqual(target['socket'],'mount')
        self.assertEqual(target['frame'],frame)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            registry.register_many([host,child])
            children=[
                {'instance':instance(host,'host'),'target':{'space':'3d','socket':'mount','frame':identity()},'motion':None,'clip':None},
                {'instance':instance(child,'child'),'target':target,'motion':None,'clip':None},
            ]
            saved=save_assembly(registry,id='joined',name='joined',origin=host['origin'],children=children)
            self.assertEqual(len(expand(registry,saved)),3)
            self.assertNotIn('interface',saved)

    def test_profile_library_rejects_pin_drift_and_duplicate_profiles(self):
        a=definition('a');b=definition('b')
        pa=interface_profile(a,[port('right','structure','structure',['structure'],.5)])
        pb=interface_profile(b,[port('left','structure','structure',['structure'],-.5)])
        value={'schema':PROFILE_LIBRARY,'profiles':[pa,pb]}
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            registry.register_many([a,b])
            self.assertEqual(validate_profile_library(value,registry),value)
            wrong=copy.deepcopy(value);wrong['profiles'][0]['sticker']['digest']='0'*64
            with self.assertRaisesRegex(ValueError,'exact sticker'):
                validate_profile_library(wrong,registry)
            duplicate=copy.deepcopy(value);duplicate['profiles'][1]=copy.deepcopy(pa)
            with self.assertRaisesRegex(ValueError,'duplicate'):
                validate_profile_library(duplicate,registry)

    def test_microforge_profiles_exercise_structural_fastener_and_axle_roles(self):
        library_tool=load_tool('build_microforge_library')
        interface_tool=load_tool('build_microforge_interfaces')
        library=library_tool.build_library();profiles=interface_tool.build_interfaces(library)
        self.assertEqual(profiles['schema'],PROFILE_LIBRARY)
        self.assertEqual(len(profiles['profiles']),12)
        self.assertEqual(sum(len(p['ports']) for p in profiles['profiles']),28)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,library)
            validate_profile_library(profiles,registry)
            by_id={p['sticker']['id']:p for p in profiles['profiles']}
            beam=by_id['micro-beam'];brace=by_id['micro-brace']
            self.assertAlmostEqual(mate_frame(beam,'right',brace,'left')[3],1.15)
            axle=by_id['micro-axle'];wheel=by_id['micro-wheel']
            self.assertEqual(match_interfaces(axle,'positive',wheel,'center')['interface'],'micro-axle')
            self.assertAlmostEqual(mate_frame(axle,'positive',wheel,'center')[7],.45)
            with self.assertRaisesRegex(ValueError,'mutually accept'):
                match_interfaces(axle,'negative',axle,'positive')
            plate=by_id['micro-plate'];pin=by_id['micro-pin']
            mounted=mate_frame(plate,'fastener-ne',pin,'bottom')
            self.assertAlmostEqual(mounted[3],.45);self.assertAlmostEqual(mounted[7],.285)
            self.assertAlmostEqual(mounted[11],-.28)


if __name__=='__main__':unittest.main()
