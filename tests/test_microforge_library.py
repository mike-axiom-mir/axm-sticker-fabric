import base64
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from axm_stickers import Registry, digest
from axm_stickers.assembly import expand, import_library, library_bundle


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'tools' / 'build_microforge_library.py'
SUMMARY = ROOT / 'examples' / 'microforge-summary.json'
GLB = 'axm.sticker.glb-rigid/v1'


class MicroforgeLibraryTests(unittest.TestCase):
    def generate(self, path):
        run = subprocess.run([sys.executable, str(GENERATOR), str(path)],
                             cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(path.read_text())

    def test_generator_is_deterministic_and_matches_inspectable_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            a = Path(temp) / 'a.json'; b = Path(temp) / 'b.json'
            first = self.generate(a); second = self.generate(b)
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(first, second)
            summary = json.loads(SUMMARY.read_text())
            self.assertEqual(first['schema'], summary['output_schema'])
            self.assertEqual(first['root'], summary['root'])
            self.assertEqual(len(first['definitions']), summary['counts']['total_definitions'])
            self.assertEqual(len(first['assets']), summary['counts']['exact_assets'])
            primitives = [d for d in first['definitions'] if 'primitive' in d['tags']]
            modules = [d for d in first['definitions'] if 'module' in d['tags']]
            self.assertEqual(len(primitives), summary['counts']['primitive_definitions'])
            self.assertEqual(len(modules), summary['counts']['module_definitions'])
            self.assertEqual({d['id'] for d in primitives}, set(summary['parts']))
            self.assertEqual({d['id'] for d in modules}, set(summary['modules']))

    def test_generated_library_imports_expands_and_roundtrips_exact_closure(self):
        with tempfile.TemporaryDirectory() as temp:
            library = self.generate(Path(temp) / 'library.json')
            with Registry(Path(temp) / 'registry.sqlite') as registry:
                pin = import_library(registry, library)
                self.assertEqual(pin, library['root'])
                root = registry.get(pin['id'], pin['version'])
                summary = json.loads(SUMMARY.read_text())
                self.assertEqual(len(expand(registry, root)), summary['counts']['expanded_records'])
                primitive_hits = registry.search(space='3d', tags=['micro','primitive'], limit=100)
                assembly_hits = registry.search(space='3d', tags=['micro','assembly'], limit=100)
                self.assertEqual(len(primitive_hits['entries']), 12)
                self.assertEqual(len(assembly_hits['entries']), 4)
                wheel_users = registry.dependents('micro-wheel', 1)['entries']
                self.assertEqual({entry['sticker']['id'] for entry in wheel_users}, {'micro-wheel-module'})
                exported = library_bundle(registry, pin['id'], pin['version'])
                self.assertEqual({digest(d) for d in exported['definitions']},
                                 {digest(d) for d in library['definitions']})
                self.assertEqual(exported['assets'], library['assets'])

    def test_every_part_retains_exact_source_and_structurally_valid_rigid_glb(self):
        with tempfile.TemporaryDirectory() as temp:
            library = self.generate(Path(temp) / 'library.json')
            assets = library['assets']
            rigid = [d for d in library['definitions'] if d['adapter'] == GLB]
            self.assertEqual(len(rigid), 12)
            for definition in rigid:
                model_ref = definition['assets']['model']
                source_ref = definition['assets']['editable-source']
                model = base64.b64decode(assets[model_ref], validate=True)
                source = base64.b64decode(assets[source_ref], validate=True)
                self.assertEqual(hashlib.sha256(model).hexdigest(), model_ref)
                self.assertEqual(hashlib.sha256(source).hexdigest(), source_ref)
                self.assertGreaterEqual(len(model), 28)
                magic, version, declared = struct.unpack('<4sII', model[:12])
                self.assertEqual((magic, version, declared), (b'glTF', 2, len(model)))
                json_length, json_kind = struct.unpack('<II', model[12:20])
                self.assertEqual(json_kind, 0x4E4F534A)
                document = json.loads(model[20:20+json_length].rstrip(b' ').decode('utf-8'))
                self.assertEqual(document['asset']['version'], '2.0')
                self.assertEqual(document['scene'], 0)
                self.assertEqual(len(document['scenes']), 1)
                self.assertNotIn('skins', document)
                self.assertFalse(document.get('images'))
                procedural = json.loads(source)
                self.assertEqual(procedural['schema'], 'axm.procedural-3d/v0.1')
                self.assertEqual(procedural['name'], definition['name'])


if __name__ == '__main__':
    unittest.main()
