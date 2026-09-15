import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_stickers import (InterfaceCatalog, Registry, digest, interface_profile,
                          save_connection_plan, solve_connection_plan,
                          validate_connection_plan)
from axm_stickers.__main__ import main as cli_main
from axm_stickers.assembly import expand, import_library, library_bundle
from axm_stickers.connections import PLAN
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
            'origin':{'author':'AXM','license':'CC0-1.0','source':'Connection fixture'},
            'adapter':'example.rigid/v1',
            'attachment':{'space':'3d','socket':'mount','anchor':identity()},
            'recipe':{},'assets':{},'parameters':{}}


def named(id,role,accepts,x):
    frame=identity();frame[3]=x
    return {'id':id,'interface':'structure','role':role,'accepts':accepts,'frame':frame}


def pin(d):
    return {'id':d['id'],'version':d['version'],'digest':digest(d)}


def endpoint(instance,port):
    return {'instance':instance,'port':port}


class ConnectionPlanTests(unittest.TestCase):
    def test_catalog_discovers_registry_verified_compatible_ports_with_cursor(self):
        beam=definition('beam');brace_a=definition('brace-a');brace_b=definition('brace-b')
        profiles={'schema':PROFILE_LIBRARY,'profiles':[
            interface_profile(beam,[named('right','structure',['brace'],.75)]),
            interface_profile(brace_a,[named('left','brace',['structure'],-.4)]),
            interface_profile(brace_b,[named('left','brace',['structure'],-.5)]),
        ]}
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            registry.register_many([beam,brace_a,brace_b]); catalog=InterfaceCatalog(registry,profiles)
            first=catalog.compatible('beam',1,'right',limit=1)
            self.assertEqual(len(first['entries']),1);self.assertFalse(first['complete'])
            second=catalog.compatible('beam',1,'right',after=first['next_cursor'],limit=10)
            self.assertTrue(second['complete'])
            self.assertEqual({first['entries'][0]['sticker']['id'],second['entries'][0]['sticker']['id']},
                             {'brace-a','brace-b'})
            with self.assertRaisesRegex(ValueError,'no named interface profile'):
                catalog.profile('missing',1)

    def test_three_part_tree_solves_and_saves_as_plain_v1_assembly(self):
        beam=definition('beam')
        profile=interface_profile(beam,[
            named('left','structure',['structure'],-.75),
            named('right','structure',['structure'],.75)])
        profiles={'schema':PROFILE_LIBRARY,'profiles':[profile]}
        plan={'schema':PLAN,'root':{'instance':'a','frame':identity()},
              'instances':[{'id':name,'sticker':pin(beam)} for name in ('a','b','c')],
              'connections':[
                  {'a':endpoint('a','right'),'b':endpoint('b','left')},
                  {'a':endpoint('b','right'),'b':endpoint('c','left')},
              ]}
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            registry.register(beam)
            solved=solve_connection_plan(registry,profiles,plan)
            frames={entry['instance']:entry['frame'] for entry in solved['frames']}
            self.assertAlmostEqual(frames['a'][3],0);self.assertAlmostEqual(frames['b'][3],1.5)
            self.assertAlmostEqual(frames['c'][3],3.0)
            saved=save_connection_plan(registry,profiles,plan,id='beam-chain',name='Beam chain',
                                       origin=beam['origin'],tags=['connection-plan-proof'])
            self.assertEqual(saved['schema'],'axm.sticker/v1')
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            self.assertNotIn('connections',saved['recipe'])
            self.assertEqual(len(expand(registry,saved)),4)
            portable=library_bundle(registry,'beam-chain',1)
            self.assertEqual({d['id'] for d in portable['definitions']},{'beam-chain','beam'})

    def test_plan_rejects_port_reuse_disconnect_and_exact_pin_drift(self):
        d=definition('part')
        profile=interface_profile(d,[
            named('left','structure',['structure'],-.5),
            named('right','structure',['structure'],.5)])
        profiles={'schema':PROFILE_LIBRARY,'profiles':[profile]}
        base={'schema':PLAN,'root':{'instance':'a','frame':identity()},
              'instances':[{'id':name,'sticker':pin(d)} for name in ('a','b','c')],
              'connections':[
                  {'a':endpoint('a','right'),'b':endpoint('b','left')},
                  {'a':endpoint('a','right'),'b':endpoint('c','left')}]}
        with self.assertRaisesRegex(ValueError,'only once'):
            validate_connection_plan(base)
        disconnected=copy.deepcopy(base);disconnected['connections']=disconnected['connections'][:1]
        with self.assertRaisesRegex(ValueError,'tree'):
            validate_connection_plan(disconnected)
        good=copy.deepcopy(base);good['connections'][1]['a']=endpoint('b','right')
        checked=validate_connection_plan(good)
        drift=copy.deepcopy(checked);drift['instances'][1]['sticker']['digest']='0'*64
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            registry.register(d)
            with self.assertRaisesRegex(ValueError,'pin does not match'):
                solve_connection_plan(registry,profiles,drift)

    def test_cli_exposes_discovery_solve_and_save_without_uc(self):
        beam=definition('beam');brace=definition('brace')
        profiles={'schema':PROFILE_LIBRARY,'profiles':[
            interface_profile(beam,[named('right','structure',['brace'],.75)]),
            interface_profile(brace,[named('left','brace',['structure'],-.4)]),
        ]}
        plan={'schema':PLAN,'root':{'instance':'beam','frame':identity()},
              'instances':[{'id':'beam','sticker':pin(beam)},{'id':'brace','sticker':pin(brace)}],
              'connections':[{'a':endpoint('beam','right'),'b':endpoint('brace','left')}]}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);database=root/'parts.sqlite';request=root/'request.json'
            with Registry(database) as registry: registry.register_many([beam,brace])
            def call(value):
                request.write_text(json.dumps(value),encoding='utf-8')
                output=io.StringIO()
                with redirect_stdout(output): cli_main([str(database),str(request)])
                return json.loads(output.getvalue())
            discovered=call({'operation':'interface_compatible','profile_library':profiles,
                             'sticker_id':'beam','version':1,'port_id':'right'})
            self.assertEqual(discovered['entries'][0]['sticker']['id'],'brace')
            solved=call({'operation':'solve_connection_plan','profile_library':profiles,'plan':plan})
            self.assertAlmostEqual({x['instance']:x['frame'] for x in solved['frames']}['brace'][3],1.15)
            saved=call({'operation':'save_connection_plan','profile_library':profiles,'plan':plan,
                        'id':'cli-joined','name':'CLI joined','origin':beam['origin']})
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            with Registry(database) as registry: self.assertEqual(len(expand(registry,registry.get('cli-joined',1))),3)

    def test_microforge_plans_cover_structural_and_axle_graphs(self):
        library_tool=load_tool('build_microforge_library')
        interface_tool=load_tool('build_microforge_interfaces')
        plan_tool=load_tool('build_microforge_connection_plans')
        library=library_tool.build_library();profiles=interface_tool.build_interfaces(library)
        examples=plan_tool.build_plans(library)
        self.assertEqual(len(examples['plans']),2)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,library);catalog=InterfaceCatalog(registry,profiles)
            beam_candidates=catalog.compatible('micro-beam',1,'right',limit=100)
            self.assertTrue(any(entry['sticker']['id']=='micro-brace' for entry in beam_candidates['entries']))
            plans={entry['id']:entry['plan'] for entry in examples['plans']}
            structural=solve_connection_plan(registry,profiles,plans['microforge-structural-plan'])
            sf={entry['instance']:entry['frame'] for entry in structural['frames']}
            self.assertEqual(len(sf),7)
            self.assertAlmostEqual(sf['beam'][3],.925)
            self.assertAlmostEqual(sf['column'][7],.775)
            self.assertAlmostEqual(sf['cap'][7],1.515)
            self.assertAlmostEqual(sf['pin'][3],1.05)
            self.assertAlmostEqual(sf['pin'][7],.285)
            axle=solve_connection_plan(registry,profiles,plans['microforge-axle-plan'])
            af={entry['instance']:entry['frame'] for entry in axle['frames']}
            self.assertAlmostEqual(af['hub'][7],-.45);self.assertAlmostEqual(af['wheel'][7],.45)


if __name__=='__main__':unittest.main()
