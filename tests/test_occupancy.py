import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_stickers import (Registry, digest, occupancy_slots, save_occupancy_plan,
                          solve_occupancy_plan, validate_occupancy_library,
                          validate_occupancy_plan)
from axm_stickers.__main__ import main as cli_main
from axm_stickers.assembly import expand, import_library, library_bundle

ROOT=Path(__file__).resolve().parents[1]


def load_tool(name):
    path=ROOT/'tools'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class OccupancyTests(unittest.TestCase):
    def setUp(self):
        library_tool=load_tool('build_microforge_library')
        interface_tool=load_tool('build_microforge_interfaces')
        occupancy_tool=load_tool('build_microforge_occupancy_examples')
        self.library=library_tool.build_library()
        self.interfaces=interface_tool.build_interfaces(self.library)
        example=occupancy_tool.build_occupancy(self.library,self.interfaces)
        self.occupancy_library=example['occupancy_library'];self.plan=example['plan']

    def test_axle_port_exposes_three_distinct_slots_and_solves_stack(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            checked=validate_occupancy_library(self.occupancy_library,registry,self.interfaces)
            self.assertEqual(len(checked['profiles']),1)
            slots=occupancy_slots(registry,self.interfaces,self.occupancy_library,'micro-axle',1,'positive')
            self.assertEqual([x['id'] for x in slots],['hub-seat','wheel-seat','detail-seat'])
            solved=solve_occupancy_plan(registry,self.interfaces,self.occupancy_library,self.plan)
            frames={x['instance']:x['frame'] for x in solved['occupants']}
            self.assertAlmostEqual(frames['hub'][7],.45)
            self.assertAlmostEqual(frames['wheel'][7],.63)
            self.assertAlmostEqual(frames['detail'][7],.76)

    def test_distinct_slots_compile_and_save_as_plain_v1_assembly(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            saved=save_occupancy_plan(registry,self.interfaces,self.occupancy_library,self.plan,
                                      id='stacked-axle',name='Stacked axle',
                                      origin=self.library['definitions'][0]['origin'],
                                      tags=['occupancy-proof'])
            self.assertEqual(saved['schema'],'axm.sticker/v1')
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            self.assertNotIn('occupancy',saved['recipe'])
            self.assertEqual(len(expand(registry,saved)),5)
            bundle=library_bundle(registry,'stacked-axle',1)
            self.assertEqual({d['id'] for d in bundle['definitions']},
                             {'stacked-axle','micro-axle','micro-hub','micro-wheel','micro-disc'})

    def test_slot_reuse_and_tree_consumed_port_are_rejected(self):
        duplicate=copy.deepcopy(self.plan)
        duplicate['occupants'][2]['host']['slot']='wheel-seat'
        with self.assertRaisesRegex(ValueError,'slot may be consumed only once'):
            validate_occupancy_plan(duplicate)
        consumed=copy.deepcopy(self.plan)
        pins={d['id']:{'id':d['id'],'version':d['version'],'digest':digest(d)}
              for d in self.library['definitions']}
        consumed['base']['instances'].append({'id':'base-bearing','sticker':pins['micro-hub']})
        consumed['base']['connections'].append(
            {'a':{'instance':'axle','port':'positive'},'b':{'instance':'base-bearing','port':'center'}})
        consumed['occupants']=consumed['occupants'][1:]
        with self.assertRaisesRegex(ValueError,'already consumed'):
            validate_occupancy_plan(consumed)

    def test_exact_profile_drift_and_unknown_slots_fail_before_save(self):
        drift=copy.deepcopy(self.occupancy_library);drift['profiles'][0]['sticker']['digest']='0'*64
        missing=copy.deepcopy(self.plan);missing['occupants'][0]['host']['slot']='missing-seat'
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            with self.assertRaisesRegex(ValueError,'exact sticker'):
                solve_occupancy_plan(registry,self.interfaces,drift,self.plan)
            with self.assertRaisesRegex(ValueError,'unknown occupancy slot'):
                solve_occupancy_plan(registry,self.interfaces,self.occupancy_library,missing)

    def test_cli_discovers_solves_and_saves_occupancy_without_uc(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);database=root/'parts.sqlite';request=root/'request.json'
            with Registry(database) as registry: import_library(registry,self.library)
            def call(value):
                request.write_text(json.dumps(value),encoding='utf-8');output=io.StringIO()
                with redirect_stdout(output): cli_main([str(database),str(request)])
                return json.loads(output.getvalue())
            slots=call({'operation':'occupancy_slots','profile_library':self.interfaces,
                        'occupancy_library':self.occupancy_library,'sticker_id':'micro-axle',
                        'version':1,'port_id':'positive'})
            self.assertEqual(len(slots),3)
            solved=call({'operation':'solve_occupancy_plan','profile_library':self.interfaces,
                         'occupancy_library':self.occupancy_library,'plan':self.plan})
            self.assertEqual(len(solved['occupants']),3)
            saved=call({'operation':'save_occupancy_plan','profile_library':self.interfaces,
                        'occupancy_library':self.occupancy_library,'plan':self.plan,
                        'id':'cli-stack','name':'CLI stack','origin':self.library['definitions'][0]['origin']})
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            with Registry(database) as registry:
                self.assertEqual(len(expand(registry,registry.get('cli-stack',1))),5)


if __name__=='__main__':unittest.main()
