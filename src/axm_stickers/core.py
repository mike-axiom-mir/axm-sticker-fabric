"""Immutable versioned creations, explicit instances, and a local registry.

This package does not import UC, render, execute recipes, contact services, or
choose a latest version. Adapters interpret declarative recipes independently.
"""
from contextlib import contextmanager
import base64
import copy
import hashlib
import json
from pathlib import Path
import re
import sqlite3

SCHEMA = 'axm.sticker/v1'
BUNDLE = 'axm.sticker-bundle/v1'
INSTANCE = 'axm.sticker-instance/v1'
DESCRIPTION = 'axm.sticker-description/v1'
REGISTRY_STATS = 'axm.sticker-registry-stats/v1'
MAX_JSON = 2 * 1024 * 1024
MAX_ASSETS = 32 * 1024 * 1024
APP = 0x41585354
REGISTRY_VERSION = 2
ASSEMBLY_ADAPTER = 'axm.sticker.assembly-3d/v1'
CREATIVE_ADAPTER = 'axm.sticker.creative-task/v1'


def encode(value):
    body = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')
    if len(body) > MAX_JSON:
        raise ValueError('definition exceeds 2 MiB')
    return body


def digest(value):
    return hashlib.sha256(encode(value)).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', value):
        raise ValueError('expected portable identifier of 1..80 characters')
    return value


def text(value, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError('expected bounded nonempty text')
    return value


def version(value):
    if type(value) is not int or not 1 <= value <= 2**31-1:
        raise ValueError('version must be a positive integer')
    return value


def sha(value):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{64}', value):
        raise ValueError('expected SHA-256 digest')
    return value


def _pin(value):
    if not isinstance(value, dict) or set(value) != {'id','version','digest'}:
        raise ValueError('dependency requires exact version pin')
    identifier(value['id']); version(value['version']); sha(value['digest'])
    return {'id':value['id'],'version':value['version'],'digest':value['digest']}


def _identifier_list(value, *, maximum=32):
    if value is None:
        return []
    if not isinstance(value, list) or len(value) > maximum or len(value) != len(set(map(str,value))):
        raise ValueError(f'expected at most {maximum} unique identifiers')
    return [identifier(item) for item in value]


def _known_dependencies(definition):
    """Return declarative dependency links plus how completely they were understood.

    The registry only indexes contracts it knows exactly. Unknown adapters are not
    guessed; malformed known contracts are surfaced as malformed instead of being
    silently treated as dependency-free.
    """
    recipe = definition['recipe']
    records = []
    try:
        if definition['adapter'] == ASSEMBLY_ADAPTER:
            if (set(recipe) != {'children'} or not isinstance(recipe['children'], list) or
                    not 1 <= len(recipe['children']) <= 4096):
                return [], 'malformed'
            for position, child in enumerate(recipe['children']):
                if not isinstance(child, dict) or 'instance' not in child:
                    return [], 'malformed'
                placed = child['instance']
                if not isinstance(placed, dict) or 'sticker' not in placed:
                    return [], 'malformed'
                records.append(('child', position, _pin(placed['sticker'])))
            return records, 'indexed'
        if definition['adapter'] == CREATIVE_ADAPTER:
            if 'dependencies' not in recipe or not isinstance(recipe['dependencies'], list):
                return [], 'malformed'
            if len(recipe['dependencies']) > 256:
                return [], 'malformed'
            for position, pin in enumerate(recipe['dependencies']):
                records.append(('dependency', position, _pin(pin)))
            return records, 'indexed'
    except ValueError:
        return [], 'malformed'
    return [], 'not_declared'


def _parameter(spec, value):
    if not isinstance(spec, dict) or not {'path','default','type'} <= spec.keys():
        raise ValueError('parameter requires path, default and type')
    kind = spec['type']
    expected = {'path','default','type'} | ({'min','max'} if kind in ('number','integer') else
                                           {'choices'} if kind == 'choice' else set())
    if set(spec) != expected:
        raise ValueError('unsupported parameter fields/type')
    if kind in ('number','integer'):
        for x in (value, spec['min'], spec['max']):
            if type(x) not in (int,float) or (kind == 'integer' and type(x) is not int):
                raise ValueError('parameter has wrong numeric type')
        if not spec['min'] <= value <= spec['max']:
            raise ValueError('parameter exceeds declared range')
    elif kind == 'boolean':
        if type(value) is not bool:
            raise ValueError('parameter requires boolean')
    elif kind == 'choice':
        choices = spec['choices']
        if not isinstance(choices,list) or not 1 <= len(choices) <= 64:
            raise ValueError('parameter requires bounded choices')
        if not any(type(value) is type(x) and value == x for x in choices):
            raise ValueError('unknown parameter choice')
    else:
        raise ValueError('unsupported parameter type')
    encode(value)


def _target(recipe, path):
    if not isinstance(path, list) or not 1 <= len(path) <= 16:
        raise ValueError('parameter path must have 1..16 segments')
    current = recipe
    for part in path:
        if isinstance(current,dict) and isinstance(part,str) and part in current:
            parent, current = current, current[part]
        elif isinstance(current,list) and type(part) is int and 0 <= part < len(current):
            parent, current = current, current[part]
        else:
            raise ValueError('parameter path does not exist in recipe')
    return parent, path[-1], current


def validate(definition):
    if not isinstance(definition,dict) or set(definition) != {
            'schema','id','version','name','tags','origin','adapter','attachment','recipe','assets','parameters'}:
        raise ValueError('unsupported sticker definition fields')
    if definition['schema'] != SCHEMA:
        raise ValueError('unsupported sticker schema')
    encode(definition)
    identifier(definition['id']); version(definition['version']); text(definition['name'],160)
    text(definition['adapter'],120)
    tags = definition['tags']
    if not isinstance(tags,list) or len(tags) > 32 or len(tags) != len(set(map(str,tags))):
        raise ValueError('expected at most 32 unique tags')
    for tag in tags: identifier(tag)
    origin = definition['origin']
    if not isinstance(origin,dict) or set(origin) != {'author','license','source'}:
        raise ValueError('author, license and source declarations required')
    for value in origin.values(): text(value)
    attachment = definition['attachment']
    if not isinstance(attachment,dict) or set(attachment) != {'space','socket','anchor'}:
        raise ValueError('attachment requires space, socket and anchor')
    identifier(attachment['socket'])
    if attachment['space'] == '2d':
        from .placement import vector
        vector(attachment['anchor'],2)
    elif attachment['space'] == '3d':
        from .placement import rigid
        rigid(attachment['anchor'])
    else:
        raise ValueError('unknown attachment space')
    assets = definition['assets']
    if not isinstance(assets,dict) or len(assets) > 64:
        raise ValueError('expected at most 64 assets')
    for key,value in assets.items(): identifier(key); sha(value)
    if not isinstance(definition['recipe'],dict):
        raise ValueError('recipe must be an object')
    parameters = definition['parameters']
    if not isinstance(parameters,dict) or len(parameters) > 64:
        raise ValueError('expected at most 64 parameters')
    paths = []
    for name,spec in parameters.items():
        identifier(name)
        if not isinstance(spec,dict): raise ValueError('invalid parameter')
        _parameter(spec, spec.get('default'))
        _,_,original = _target(definition['recipe'], spec['path'])
        if type(original) is not type(spec['default']) or original != spec['default']:
            raise ValueError('parameter default must equal canonical recipe value')
        path = spec['path']
        if any(path[:len(p)] == p or p[:len(path)] == path for p in paths):
            raise ValueError('parameter paths must not overlap')
        paths.append(path)
    return copy.deepcopy(definition)


def instance(definition, id, *, overrides=None, placement=None):
    validate(definition); identifier(id)
    result = {'schema':INSTANCE,'id':id,'sticker':{'id':definition['id'],
              'version':definition['version'],'digest':digest(definition)},
              'overrides':copy.deepcopy({} if overrides is None else overrides),'placement':copy.deepcopy({} if placement is None else placement)}
    resolve(definition,result)
    return result


def resolve(definition, placed):
    validate(definition)
    if not isinstance(placed,dict) or set(placed) != {'schema','id','sticker','overrides','placement'}:
        raise ValueError('unsupported instance fields')
    identifier(placed['id'])
    pin = placed['sticker']
    if not isinstance(pin,dict) or set(pin) != {'id','version','digest'}:
        raise ValueError('instance requires exact version pin')
    identifier(pin['id']); version(pin['version']); sha(pin['digest'])
    if placed['schema'] != INSTANCE or placed['sticker'] != {
            'id':definition['id'],'version':definition['version'],'digest':digest(definition)}:
        raise ValueError('instance does not match its pinned sticker version')
    if not isinstance(placed['placement'],dict): raise ValueError('placement must be an object')
    overrides = placed['overrides']
    if not isinstance(overrides,dict) or set(overrides)-definition['parameters'].keys():
        raise ValueError('undeclared parameter override')
    recipe = copy.deepcopy(definition['recipe'])
    for name,value in overrides.items():
        spec = definition['parameters'][name]
        _parameter(spec,value)
        parent,key,_ = _target(recipe,spec['path'])
        parent[key] = copy.deepcopy(value)
    encode(placed)
    return recipe


class Registry:
    """One offline file: indexed metadata, composition graph and exact asset bytes."""
    def __init__(self,path):
        self.db = sqlite3.connect(Path(path), timeout=35, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        try:
            self.db.execute('PRAGMA foreign_keys=ON')
            self.db.execute('PRAGMA synchronous=FULL')
            with self._write():
                app = self.db.execute('PRAGMA application_id').fetchone()[0]
                tables = self.db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if app != APP and (app or tables): raise ValueError('not a sticker registry')
                v = self.db.execute('PRAGMA user_version').fetchone()[0]
                if v not in (0,1,REGISTRY_VERSION) or (app == APP and v not in (1,REGISTRY_VERSION)):
                    raise ValueError('unsupported registry version')
                if not tables:
                    for sql in (
                        'CREATE TABLE assets (digest TEXT PRIMARY KEY, body BLOB NOT NULL)',
                        'CREATE TABLE stickers (id TEXT, version INTEGER, digest TEXT UNIQUE, adapter TEXT, socket TEXT, body TEXT, PRIMARY KEY(id,version))',
                        'CREATE TABLE tags (id TEXT, version INTEGER, tag TEXT, PRIMARY KEY(id,version,tag), FOREIGN KEY(id,version) REFERENCES stickers(id,version))',
                        'CREATE INDEX sticker_adapter ON stickers(adapter,socket)',
                        'CREATE INDEX sticker_tags ON tags(tag,id,version)'):
                        self.db.execute(sql)
                    self.db.execute(f'PRAGMA application_id={APP}')
                    self.db.execute('PRAGMA user_version=1')
                    v = 1
                if v == 1:
                    self._create_discovery_tables()
                    self._rebuild_discovery_index()
                    self.db.execute(f'PRAGMA user_version={REGISTRY_VERSION}')
                present = {row[0] for row in self.db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'")}
                required = {'assets','stickers','tags','discovery','links'}
                if not required <= present:
                    raise ValueError('corrupt sticker registry schema')
            size = self.db.execute('PRAGMA page_size').fetchone()[0]
            self.db.execute(f'PRAGMA max_page_count={512*1024*1024//size}')
        except BaseException:
            self.db.close(); raise

    def _create_discovery_tables(self):
        for sql in (
            'CREATE TABLE IF NOT EXISTS discovery (id TEXT, version INTEGER, space TEXT NOT NULL, dependency_state TEXT NOT NULL, PRIMARY KEY(id,version), FOREIGN KEY(id,version) REFERENCES stickers(id,version) ON DELETE CASCADE)',
            'CREATE TABLE IF NOT EXISTS links (source_id TEXT, source_version INTEGER, relation TEXT, position INTEGER, target_id TEXT, target_version INTEGER, target_digest TEXT, PRIMARY KEY(source_id,source_version,relation,position), FOREIGN KEY(source_id,source_version) REFERENCES stickers(id,version) ON DELETE CASCADE)',
            'CREATE INDEX IF NOT EXISTS sticker_space ON discovery(space,id,version)',
            'CREATE INDEX IF NOT EXISTS link_target ON links(target_id,target_version,target_digest,source_id,source_version)'):
            self.db.execute(sql)

    def _rebuild_discovery_index(self):
        self.db.execute('DELETE FROM links')
        self.db.execute('DELETE FROM discovery')
        for row in self.db.execute('SELECT body FROM stickers ORDER BY rowid').fetchall():
            self._index_definition(validate(json.loads(row[0])))

    def _index_definition(self,definition):
        records,state = _known_dependencies(definition)
        self.db.execute('DELETE FROM links WHERE source_id=? AND source_version=?',
                        (definition['id'],definition['version']))
        self.db.execute('INSERT OR REPLACE INTO discovery VALUES (?,?,?,?)',
                        (definition['id'],definition['version'],
                         definition['attachment']['space'],state))
        for relation,position,pin in records:
            self.db.execute('INSERT INTO links VALUES (?,?,?,?,?,?,?)',
                            (definition['id'],definition['version'],relation,position,
                             pin['id'],pin['version'],pin['digest']))

    @contextmanager
    def _write(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction: self.db.execute('ROLLBACK')
            raise

    def __enter__(self): return self
    def __exit__(self,*args): self.db.close()

    def register(self,definition,assets=None):
        return self.register_many([definition],assets)[0]

    def register_many(self,definitions,assets=None):
        """Explicit bounded batch, one atomic durable commit, shared exact bytes."""
        if not isinstance(definitions,list) or not 1 <= len(definitions) <= 4096:
            raise ValueError('batch requires 1..4096 definitions')
        definitions = [validate(d) for d in definitions]
        if sum(len(encode(d)) for d in definitions) > 16*MAX_JSON:
            raise ValueError('batch definition byte budget exceeded')
        assets = {} if assets is None else assets
        declared = {s for d in definitions for s in d['assets'].values()}
        if not isinstance(assets,dict) or set(assets)-declared:
            raise ValueError('supplied assets must be referenced digests')
        if any(not isinstance(v,bytes) for v in assets.values()) or sum(map(len,assets.values())) > MAX_ASSETS:
            raise ValueError('asset bytes exceed 32 MiB')
        with self._write():
            return [self._register(d,{s:assets[s] for s in set(d['assets'].values()) if s in assets})
                    for d in definitions]

    def _register(self,definition,assets):
        existing = self.db.execute('SELECT digest FROM stickers WHERE id=? AND version=?',
                                   (definition['id'],definition['version'])).fetchone()
        key = digest(definition)
        if existing and existing[0] != key:
            raise ValueError('immutable version conflict; register a new version')
        total_bytes = 0
        for reference in set(definition['assets'].values()):
            if reference in assets:
                body = assets[reference]
                if hashlib.sha256(body).hexdigest() != reference: raise ValueError('asset digest mismatch')
                self.db.execute('INSERT OR IGNORE INTO assets VALUES (?,?)',(reference,body))
            total_bytes += len(self.asset(reference))
            if total_bytes > MAX_ASSETS: raise ValueError('referenced assets exceed 32 MiB')
        self.db.execute('INSERT OR IGNORE INTO stickers VALUES (?,?,?,?,?,?)',
                        (definition['id'],definition['version'],key,definition['adapter'],
                         definition['attachment']['socket'],encode(definition).decode()))
        for tag in definition['tags']:
            self.db.execute('INSERT OR IGNORE INTO tags VALUES (?,?,?)',
                            (definition['id'],definition['version'],tag))
        self._index_definition(definition)
        return {'id':definition['id'],'version':definition['version'],'digest':key}

    def get(self,id,ver):
        identifier(id); version(ver)
        row = self.db.execute('SELECT digest,body FROM stickers WHERE id=? AND version=?',(id,ver)).fetchone()
        if row is None: raise ValueError('unknown sticker version')
        definition = json.loads(row[1])
        if digest(definition) != row[0]: raise ValueError('corrupt sticker definition')
        return validate(definition)

    def asset(self,reference):
        sha(reference)
        row = self.db.execute('SELECT body FROM assets WHERE digest=?',(reference,)).fetchone()
        if row is None or hashlib.sha256(row[0]).hexdigest() != reference:
            raise ValueError('missing or corrupt asset')
        return row[0]

    def search(self, *, adapter=None, socket=None, space=None, tag=None, tags=None,
               any_tags=None, depends_on=None, after=0, limit=30):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid search cursor/limit')
        clauses,values = ['s.rowid>?'],[after]
        for key,value in (('adapter',adapter),('socket',socket)):
            if value is not None: text(value,120); clauses.append(f's.{key}=?'); values.append(value)
        if space is not None:
            if space not in ('2d','3d'): raise ValueError('unknown attachment space')
            clauses.append('d.space=?'); values.append(space)
        all_tags = _identifier_list(tags)
        if tag is not None:
            all_tags = [identifier(tag)] + all_tags
        if len(all_tags) != len(set(all_tags)):
            raise ValueError('duplicate required tag')
        for required in all_tags:
            clauses.append('EXISTS (SELECT 1 FROM tags t WHERE t.id=s.id AND t.version=s.version AND t.tag=?)')
            values.append(required)
        any_tags = _identifier_list(any_tags)
        if any_tags:
            placeholders=','.join('?' for _ in any_tags)
            clauses.append(f'EXISTS (SELECT 1 FROM tags t WHERE t.id=s.id AND t.version=s.version AND t.tag IN ({placeholders}))')
            values.extend(any_tags)
        if depends_on is not None:
            if not isinstance(depends_on,dict) or set(depends_on) not in ({'id','version'},{'id','version','digest'}):
                raise ValueError('depends_on requires id/version and optional digest')
            identifier(depends_on['id']); version(depends_on['version'])
            clause = ('EXISTS (SELECT 1 FROM links l WHERE l.source_id=s.id AND l.source_version=s.version '
                      'AND l.target_id=? AND l.target_version=?')
            values.extend([depends_on['id'],depends_on['version']])
            if 'digest' in depends_on:
                sha(depends_on['digest']); clause += ' AND l.target_digest=?'; values.append(depends_on['digest'])
            clauses.append(clause+')')
        rows = self.db.execute(
            'SELECT s.rowid,s.body,s.digest FROM stickers s JOIN discovery d ON d.id=s.id AND d.version=s.version WHERE '+
            ' AND '.join(clauses)+' ORDER BY s.rowid LIMIT ?',values+[limit]).fetchall()
        results = []
        for row in rows:
            d = json.loads(row[1])
            results.append({k:d[k] for k in ('id','version','name','tags','adapter','attachment','origin')}
                           | {'digest':row[2]})
        return {'entries':results,'next_cursor':rows[-1][0] if rows else after}

    def dependencies(self,id,ver):
        definition = self.get(id,ver)
        state = self.db.execute('SELECT dependency_state FROM discovery WHERE id=? AND version=?',
                                (id,ver)).fetchone()
        rows = self.db.execute(
            'SELECT relation,position,target_id,target_version,target_digest FROM links '
            'WHERE source_id=? AND source_version=? ORDER BY relation,position',(id,ver)).fetchall()
        entries=[]
        for row in rows:
            target=self.db.execute('SELECT digest FROM stickers WHERE id=? AND version=?',
                                   (row['target_id'],row['target_version'])).fetchone()
            availability = ('missing' if target is None else
                            'exact' if target['digest']==row['target_digest'] else 'digest_mismatch')
            entries.append({'relation':row['relation'],'position':row['position'],
                            'sticker':{'id':row['target_id'],'version':row['target_version'],
                                       'digest':row['target_digest']},
                            'availability':availability})
        return {'sticker':{'id':definition['id'],'version':definition['version'],
                           'digest':digest(definition)},
                'index_state':state['dependency_state'],'entries':entries}

    def dependents(self,id,ver,*,after=0,limit=100):
        definition=self.get(id,ver); key=digest(definition)
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid search cursor/limit')
        rows=self.db.execute(
            'SELECT l.rowid,l.relation,l.position,s.id,s.version,s.digest FROM links l '
            'JOIN stickers s ON s.id=l.source_id AND s.version=l.source_version '
            'WHERE l.rowid>? AND l.target_id=? AND l.target_version=? AND l.target_digest=? '
            'ORDER BY l.rowid LIMIT ?',(after,id,ver,key,limit)).fetchall()
        entries=[{'relation':row['relation'],'position':row['position'],
                  'sticker':{'id':row['id'],'version':row['version'],'digest':row['digest']}}
                 for row in rows]
        return {'sticker':{'id':id,'version':ver,'digest':key},'entries':entries,
                'next_cursor':rows[-1]['rowid'] if rows else after}

    def describe(self,id,ver):
        definition=self.get(id,ver); key=digest(definition)
        references=sorted(set(definition['assets'].values()))
        total=sum(len(self.asset(reference)) for reference in references)
        dependent_count=self.db.execute(
            'SELECT count(*) FROM links WHERE target_id=? AND target_version=? AND target_digest=?',
            (id,ver,key)).fetchone()[0]
        deps=self.dependencies(id,ver)
        return {'schema':DESCRIPTION,'sticker':{'id':id,'version':ver,'digest':key},
                'metadata':{k:copy.deepcopy(definition[k]) for k in
                            ('name','tags','adapter','attachment','origin')},
                'parameters':sorted(definition['parameters']),
                'assets':{'count':len(references),'bytes':total,'names':sorted(definition['assets'])},
                'dependencies':{'index_state':deps['index_state'],'entries':deps['entries']},
                'dependents':{'count':dependent_count}}

    def stats(self,*,adapter_limit=256):
        if type(adapter_limit) is not int or not 1 <= adapter_limit <= 4096:
            raise ValueError('adapter_limit must be 1..4096')
        sticker_versions=self.db.execute('SELECT count(*) FROM stickers').fetchone()[0]
        sticker_ids=self.db.execute('SELECT count(DISTINCT id) FROM stickers').fetchone()[0]
        assets=self.db.execute('SELECT count(*),coalesce(sum(length(body)),0) FROM assets').fetchone()
        links=self.db.execute('SELECT count(*) FROM links').fetchone()[0]
        by_space={row['space']:row['n'] for row in self.db.execute(
            'SELECT space,count(*) AS n FROM discovery GROUP BY space ORDER BY space')}
        adapters=self.db.execute(
            'SELECT adapter,count(*) AS n FROM stickers GROUP BY adapter ORDER BY adapter LIMIT ?',
            (adapter_limit+1,)).fetchall()
        by_adapter={row['adapter']:row['n'] for row in adapters[:adapter_limit]}
        states={row['dependency_state']:row['n'] for row in self.db.execute(
            'SELECT dependency_state,count(*) AS n FROM discovery GROUP BY dependency_state ORDER BY dependency_state')}
        return {'schema':REGISTRY_STATS,'registry_version':REGISTRY_VERSION,
                'stickers':{'ids':sticker_ids,'versions':sticker_versions},
                'assets':{'count':assets[0],'bytes':assets[1]},'links':links,
                'by_space':by_space,'by_adapter':by_adapter,
                'adapter_truncated':len(adapters)>adapter_limit,'dependency_index':states}

    def bundle(self,id,ver):
        definition = self.get(id,ver)
        return {'schema':BUNDLE,'definition':definition,'assets':{
                s:base64.b64encode(self.asset(s)).decode('ascii') for s in sorted(set(definition['assets'].values()))}}

    def import_bundle(self,bundle):
        if not isinstance(bundle,dict) or set(bundle) != {'schema','definition','assets'} or bundle['schema'] != BUNDLE:
            raise ValueError('invalid sticker bundle')
        definition = validate(bundle['definition'])
        if not isinstance(bundle['assets'],dict) or set(bundle['assets']) != set(definition['assets'].values()):
            raise ValueError('bundle must contain exactly its declared assets')
        if any(not isinstance(v,str) for v in bundle['assets'].values()) or sum(map(len,bundle['assets'].values())) > 45*1024*1024:
            raise ValueError('bundle exceeds byte bound')
        return self.register(definition,{k:base64.b64decode(v,validate=True) for k,v in bundle['assets'].items()})
