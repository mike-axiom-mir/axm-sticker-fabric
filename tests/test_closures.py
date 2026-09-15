import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_stickers import (Registry, save_closed_connection_plan,
                          validate_closure_set, verify_loop_closures)
from axm_stickers.__main__ import main as cli_main
from axm_stickers.assembly import expand, import_library, library_bundle

ROOT=Path(__file__).resolve().parents[1]


def load_tool(name):
    path=ROOT/'tools'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


class LoopClosureTests(unittest.TestCase):
    def setUp(self):
        library_tool=load_tool('build_microforge_library')
        interface_tool=load_tool('build_microforge_interfaces')
        closure_tool=load_tool('build_microforge_closure_examples')
        self.library=library_tool.build_library()
        self.profiles=interface_tool.build_interfaces(self.library)
        self.closure=closure_tool.build_closure(self.library)

    def test_microforge_loop_closes_without_adjusting_tree_solution(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            report=verify_loop_closures(registry,self.profiles,self.closure)
            self.assertTrue(report['all_closed'])
            self.assertEqual(len(report['closures']),1)
            check=report['closures'][0]
            self.assertTrue(check['closed'])
            self.assertLessEqual(check['residual']['translation'],1e-12)
            self.assertLessEqual(check['residual']['rotation'],1e-12)
            saved=save_closed_connection_plan(
                registry,self.profiles,self.closure,id='microforge-loop-proof',
                name='Microforge loop proof',origin=self.library['definitions'][0]['origin'],
                tags=['loop-closure-proof'])
            self.assertEqual(saved['schema'],'axm.sticker/v1')
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            self.assertEqual(len(expand(registry,saved)),5)
            bundle=library_bundle(registry,'microforge-loop-proof',1)
            self.assertEqual({d['id'] for d in bundle['definitions']},
                             {'microforge-loop-proof','micro-cube','micro-beam'})

    def test_inconsistent_extra_edge_reports_residual_and_cannot_save(self):
        broken=copy.deepcopy(self.closure)
        broken['closures'][0]['b']['port']='y-neg'
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            report=verify_loop_closures(registry,self.profiles,broken)
            self.assertFalse(report['all_closed'])
            self.assertFalse(report['closures'][0]['closed'])
            self.assertGreater(report['closures'][0]['residual']['translation'],
                               broken['tolerance']['translation'])
            with self.assertRaisesRegex(ValueError,'does not close'):
                save_closed_connection_plan(
                    registry,self.profiles,broken,id='bad-loop',name='bad loop',
                    origin=self.library['definitions'][0]['origin'])

    def test_closure_ports_remain_single_occupancy_and_tolerances_are_bounded(self):
        reused=copy.deepcopy(self.closure)
        reused['closures'][0]['b']['port']='x-pos'
        with self.assertRaisesRegex(ValueError,'only once'):
            validate_closure_set(reused)
        negative=copy.deepcopy(self.closure);negative['tolerance']['translation']=-1
        with self.assertRaisesRegex(ValueError,'translation tolerance'):
            validate_closure_set(negative)
        huge_rotation=copy.deepcopy(self.closure);huge_rotation['tolerance']['rotation']=2.1
        with self.assertRaisesRegex(ValueError,'rotation tolerance'):
            validate_closure_set(huge_rotation)

    def test_closure_report_is_bidirectional_and_does_not_claim_geometry(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            report=verify_loop_closures(registry,self.profiles,self.closure)
            entry=report['closures'][0]
            self.assertEqual(entry['interface'],'micro-structure')
            self.assertEqual(set(entry['residual']),{'translation','rotation'})
            self.assertNotIn('collision',report)
            self.assertNotIn('geometry',report)
            self.assertNotIn('physics',report)

    def test_cli_verifies_and_saves_closed_loop_without_uc(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);database=root/'parts.sqlite';request=root/'request.json'
            with Registry(database) as registry: import_library(registry,self.library)
            def call(value):
                request.write_text(json.dumps(value),encoding='utf-8')
                output=io.StringIO()
                with redirect_stdout(output): cli_main([str(database),str(request)])
                return json.loads(output.getvalue())
            report=call({'operation':'verify_loop_closures','profile_library':self.profiles,
                         'closure_set':self.closure})
            self.assertTrue(report['all_closed'])
            saved=call({'operation':'save_closed_connection_plan','profile_library':self.profiles,
                        'closure_set':self.closure,'id':'cli-loop','name':'CLI loop',
                        'origin':self.library['definitions'][0]['origin']})
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            with Registry(database) as registry:
                self.assertEqual(len(expand(registry,registry.get('cli-loop',1))),5)


if __name__=='__main__':unittest.main()
