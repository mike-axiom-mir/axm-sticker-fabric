import copy
from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_stickers import (Registry, digest, extract_selection, save_selection_as_sticker,
                          selection_manifest, validate_selection)
from axm_stickers.__main__ import main as cli_main
from axm_stickers.assembly import expand, import_library, library_bundle
from axm_stickers.interfaces import port
from axm_stickers.selection import SELECTION

ROOT=Path(__file__).resolve().parents[1]


def load_tool(name):
    path=ROOT/'tools'/f'{name}.py'
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


class SelectionTests(unittest.TestCase):
    def setUp(self):
        library_tool=load_tool('build_microforge_library')
        interface_tool=load_tool('build_microforge_interfaces')
        self.library=library_tool.build_library()
        self.interfaces=interface_tool.build_interfaces(self.library)
        self.selection={'schema':SELECTION,'source':copy.deepcopy(self.library['root']),
                        'paths':['root/corner-0/beam-x','root/corner-0/column','root/corner-0/cap'],
                        'anchor':'root/corner-0/beam-x'}

    def test_manifest_and_nested_selection_rebase_exact_targets(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            manifest=selection_manifest(registry,self.library['root'])
            paths={entry['path'] for entry in manifest['entries']}
            self.assertIn('root/corner-0/beam-x',paths)
            self.assertIn('root/panel-1/marker',paths)
            extracted=extract_selection(registry,self.selection)
            targets={item['path']:item['target']['frame'] for item in extracted['items']}
            self.assertAlmostEqual(targets['root/corner-0/beam-x'][3],0)
            self.assertAlmostEqual(targets['root/corner-0/beam-x'][7],0)
            self.assertAlmostEqual(targets['root/corner-0/column'][3],-.70)
            self.assertAlmostEqual(targets['root/corner-0/column'][7],.52)
            self.assertAlmostEqual(targets['root/corner-0/cap'][3],-.70)
            self.assertAlmostEqual(targets['root/corner-0/cap'][7],1.22)

    def test_selection_saves_plain_v1_with_exact_receipt_and_exposed_ports(self):
        expose=[{'path':'root/corner-0/beam-x','port':'left','id':'module-left'},
                {'path':'root/corner-0/column','port':'top','id':'module-top'}]
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            result=save_selection_as_sticker(
                registry,self.selection,id='captured-corner-slice',name='Captured corner slice',
                author='AXM',license='CC0-1.0',tags=['selection-proof'],
                interface_library=self.interfaces,expose=expose)
            saved=result['sticker']; profile=result['interface_profile']
            self.assertEqual(saved['schema'],'axm.sticker/v1')
            self.assertEqual(saved['adapter'],'axm.sticker.assembly-3d/v1')
            self.assertEqual(result['receipt']['source'],self.library['root'])
            self.assertIn(self.library['root']['digest'],saved['origin']['source'])
            self.assertEqual(profile['sticker'],{'id':saved['id'],'version':saved['version'],
                                                 'digest':digest(saved)})
            left=port(profile,'module-left'); top=port(profile,'module-top')
            self.assertAlmostEqual(left['frame'][3],-.75)
            self.assertAlmostEqual(left['frame'][7],0)
            self.assertAlmostEqual(top['frame'][3],-.70)
            self.assertAlmostEqual(top['frame'][7],1.12)
            self.assertEqual(len(expand(registry,saved)),4)
            bundle=library_bundle(registry,'captured-corner-slice',1)
            self.assertEqual({definition['id'] for definition in bundle['definitions']},
                             {'captured-corner-slice','micro-beam','micro-column','micro-cap'})

    def test_duplicate_nested_instance_ids_are_renamed_deterministically(self):
        selection={'schema':SELECTION,'source':copy.deepcopy(self.library['root']),
                   'paths':['root/corner-0/beam-x','root/corner-1/beam-x'],
                   'anchor':'root/corner-0/beam-x'}
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            first=extract_selection(registry,selection);second=extract_selection(registry,selection)
            first_ids=[item['saved_instance'] for item in first['items']]
            self.assertEqual(first_ids,[item['saved_instance'] for item in second['items']])
            self.assertEqual(len(first_ids),len(set(first_ids)))
            self.assertTrue(all(len(value)<=80 for value in first_ids))

    def test_overlap_pin_drift_and_unknown_path_fail_closed(self):
        overlap={'schema':SELECTION,'source':copy.deepcopy(self.library['root']),
                 'paths':['root/corner-0','root/corner-0/beam-x'],'anchor':'root/corner-0'}
        with self.assertRaisesRegex(ValueError,'ancestor'):
            validate_selection(overlap)
        drift=copy.deepcopy(self.selection);drift['source']['digest']='0'*64
        missing=copy.deepcopy(self.selection);missing['paths'][0]='root/corner-0/missing';missing['anchor']='root/corner-0/missing'
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp)/'parts.sqlite') as registry:
            import_library(registry,self.library)
            with self.assertRaisesRegex(ValueError,'source pin'):
                extract_selection(registry,drift)
            with self.assertRaisesRegex(ValueError,'does not exist'):
                extract_selection(registry,missing)

    def test_cli_lists_previews_and_saves_selection_without_uc(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);database=root/'parts.sqlite';request=root/'request.json'
            with Registry(database) as registry: import_library(registry,self.library)
            def call(value):
                request.write_text(json.dumps(value),encoding='utf-8');output=io.StringIO()
                with redirect_stdout(output): cli_main([str(database),str(request)])
                return json.loads(output.getvalue())
            manifest=call({'operation':'selection_manifest','source':self.library['root']})
            self.assertTrue(any(entry['path']=='root/corner-0/beam-x' for entry in manifest['entries']))
            preview=call({'operation':'extract_selection','selection':self.selection})
            self.assertEqual(len(preview['items']),3)
            saved=call({'operation':'save_selection_as_sticker','selection':self.selection,
                        'id':'cli-capture','name':'CLI capture','author':'AXM','license':'CC0-1.0'})
            self.assertEqual(saved['sticker']['adapter'],'axm.sticker.assembly-3d/v1')
            with Registry(database) as registry:
                self.assertEqual(len(expand(registry,registry.get('cli-capture',1))),4)


if __name__=='__main__':unittest.main()
