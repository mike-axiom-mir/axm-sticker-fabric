import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from axm_stickers import Registry, digest, instance
from axm_stickers.core import APP, ASSEMBLY_ADAPTER, CREATIVE_ADAPTER, REGISTRY_VERSION, SCHEMA
from axm_stickers.placement import identity


def definition(id, *, tags=(), space='3d', adapter='example.rigid/v1', recipe=None):
    attachment = ({'space':'3d','socket':'mount','anchor':identity()} if space == '3d'
                  else {'space':'2d','socket':'surface','anchor':[0,0]})
    return {'schema':SCHEMA,'id':id,'version':1,'name':id,'tags':list(tags),
            'origin':{'author':'AXM','license':'CC0-1.0','source':'Discovery fixture'},
            'adapter':adapter,'attachment':attachment,'recipe':{} if recipe is None else recipe,
            'assets':{},'parameters':{}}


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)

    def test_graph_indexes_exact_assembly_and_creative_dependencies(self):
        with Registry(self.root/'registry.sqlite') as r:
            source=definition('source',tags=['metal','tiny'])
            r.register(source)
            pin=instance(source,'source-instance')['sticker']
            group=definition('group',tags=['assembly'],adapter=ASSEMBLY_ADAPTER,
                recipe={'children':[{'instance':instance(source,'child'),
                                     'target':{'space':'3d','socket':'mount','frame':identity()},
                                     'motion':None,'clip':None}]})
            creative=definition('creative',tags=['recipe'],space='2d',adapter=CREATIVE_ADAPTER,
                                recipe={'dependencies':[pin]})
            r.register_many([group,creative])

            deps=r.dependencies('group',1)
            self.assertEqual(deps['index_state'],'indexed')
            self.assertEqual(deps['entries'][0]['sticker'],pin)
            self.assertEqual(deps['entries'][0]['availability'],'exact')
            self.assertEqual({x['sticker']['id'] for x in r.dependents('source',1)['entries']},
                             {'group','creative'})
            self.assertEqual({x['id'] for x in r.search(depends_on={'id':'source','version':1})['entries']},
                             {'group','creative'})

    def test_discovery_searches_space_required_tags_and_any_tags(self):
        with Registry(self.root/'registry.sqlite') as r:
            r.register_many([definition('metal-small',tags=['metal','small']),
                             definition('metal-large',tags=['metal','large']),
                             definition('flat',tags=['ui','small'],space='2d')])
            self.assertEqual([x['id'] for x in r.search(space='3d',tags=['metal','small'])['entries']],
                             ['metal-small'])
            self.assertEqual({x['id'] for x in r.search(any_tags=['large','ui'])['entries']},
                             {'metal-large','flat'})
            with self.assertRaises(ValueError):
                r.search(tags=['metal'],tag='metal')

    def test_describe_and_stats_report_registry_facts_without_render_claims(self):
        with Registry(self.root/'registry.sqlite') as r:
            r.register(definition('part',tags=['tiny']))
            described=r.describe('part',1)
            self.assertEqual(described['schema'],'axm.sticker-description/v1')
            self.assertEqual(described['dependencies']['index_state'],'not_declared')
            self.assertEqual(described['assets'],{'count':0,'bytes':0,'names':[]})
            stats=r.stats()
            self.assertEqual(stats['registry_version'],REGISTRY_VERSION)
            self.assertEqual(stats['stickers'],{'ids':1,'versions':1})
            self.assertEqual(stats['by_space'],{'3d':1})

    def test_known_malformed_dependency_contract_is_visible_not_guessed(self):
        with Registry(self.root/'registry.sqlite') as r:
            malformed=definition('bad',adapter=ASSEMBLY_ADAPTER,recipe={'children':'not-a-list'})
            r.register(malformed)
            self.assertEqual(r.dependencies('bad',1),
                {'sticker':{'id':'bad','version':1,'digest':digest(malformed)},
                 'index_state':'malformed','entries':[]})

    def test_v1_registry_migrates_in_place_and_backfills_discovery(self):
        path=self.root/'old.sqlite'; d=definition('legacy',tags=['old'])
        db=sqlite3.connect(path)
        for sql in (
            'CREATE TABLE assets (digest TEXT PRIMARY KEY, body BLOB NOT NULL)',
            'CREATE TABLE stickers (id TEXT, version INTEGER, digest TEXT UNIQUE, adapter TEXT, socket TEXT, body TEXT, PRIMARY KEY(id,version))',
            'CREATE TABLE tags (id TEXT, version INTEGER, tag TEXT, PRIMARY KEY(id,version,tag), FOREIGN KEY(id,version) REFERENCES stickers(id,version))',
            'CREATE INDEX sticker_adapter ON stickers(adapter,socket)',
            'CREATE INDEX sticker_tags ON tags(tag,id,version)'):
            db.execute(sql)
        db.execute('INSERT INTO stickers VALUES (?,?,?,?,?,?)',
                   (d['id'],d['version'],digest(d),d['adapter'],d['attachment']['socket'],
                    json.dumps(d,sort_keys=True,separators=(',',':'))))
        db.execute('INSERT INTO tags VALUES (?,?,?)',('legacy',1,'old'))
        db.execute(f'PRAGMA application_id={APP}'); db.execute('PRAGMA user_version=1')
        db.commit(); db.close()

        with Registry(path) as r:
            self.assertEqual(r.db.execute('PRAGMA user_version').fetchone()[0],REGISTRY_VERSION)
            self.assertEqual([x['id'] for x in r.search(space='3d',tags=['old'])['entries']],['legacy'])


if __name__ == '__main__':
    unittest.main()
