"""Experimental named rigid interfaces layered above immutable sticker v1 pins.

This module does not change sticker definitions, registry storage, bundle schemas,
or renderer behavior. Interface profiles are exact-pin companion data used for
bounded authoring experiments before any sticker-schema expansion is considered.
"""
import copy

from .core import digest, encode, identifier, sha, validate, version
from .placement import identity, inverse_rigid, multiply, rigid

PROFILE = 'axm.sticker-interface-profile/v0.1'
PROFILE_LIBRARY = 'axm.sticker-interface-library/v0.1'
MATCH = 'axm.sticker-interface-match/v0.1'
MAX_PORTS = 64
MAX_ACCEPTS = 16
MAX_PROFILES = 4096


def _pin(value):
    if not isinstance(value, dict) or set(value) != {'id','version','digest'}:
        raise ValueError('interface profile requires an exact sticker pin')
    identifier(value['id']); version(value['version']); sha(value['digest'])
    return {'id':value['id'],'version':value['version'],'digest':value['digest']}


def _roles(value):
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_ACCEPTS:
        raise ValueError(f'port accepts requires 1..{MAX_ACCEPTS} roles')
    checked = [identifier(role) for role in value]
    if len(checked) != len(set(checked)):
        raise ValueError('port accepts roles must be unique')
    return checked


def _compatible(a,b):
    return (a['interface'] == b['interface'] and
            b['role'] in a['accepts'] and a['role'] in b['accepts'])


def validate_profile(profile, definition=None):
    """Validate one exact-pin multi-port companion profile.

    A port frame is the local mating coordinate frame, not a surface normal.
    Two mated ports are aligned by making those frames identical.
    """
    if not isinstance(profile, dict) or set(profile) != {'schema','sticker','ports'}:
        raise ValueError('unsupported interface profile fields')
    if profile['schema'] != PROFILE:
        raise ValueError('unsupported interface profile schema')
    pin = _pin(profile['sticker'])
    ports = profile['ports']
    if not isinstance(ports, list) or not 1 <= len(ports) <= MAX_PORTS:
        raise ValueError(f'interface profile requires 1..{MAX_PORTS} ports')
    seen = set()
    for port in ports:
        if not isinstance(port, dict) or set(port) != {'id','interface','role','accepts','frame'}:
            raise ValueError('port requires id, interface, role, accepts and frame')
        port_id = identifier(port['id'])
        if port_id in seen:
            raise ValueError('port ids must be unique within one profile')
        seen.add(port_id)
        identifier(port['interface']); identifier(port['role']); _roles(port['accepts'])
        rigid(port['frame'])
    if definition is not None:
        d = validate(definition)
        if d['attachment']['space'] != '3d':
            raise ValueError('named rigid interface profiles require a 3d sticker')
        expected = {'id':d['id'],'version':d['version'],'digest':digest(d)}
        if pin != expected:
            raise ValueError('interface profile does not match exact sticker definition')
    encode(profile)
    return copy.deepcopy(profile)


def interface_profile(definition, ports):
    d = validate(definition)
    if d['attachment']['space'] != '3d':
        raise ValueError('named rigid interface profiles require a 3d sticker')
    return validate_profile({'schema':PROFILE,
        'sticker':{'id':d['id'],'version':d['version'],'digest':digest(d)},
        'ports':copy.deepcopy(ports)}, d)


def validate_profile_library(value, registry=None):
    if not isinstance(value, dict) or set(value) != {'schema','profiles'}:
        raise ValueError('unsupported interface profile library fields')
    if value['schema'] != PROFILE_LIBRARY:
        raise ValueError('unsupported interface profile library schema')
    profiles = value['profiles']
    if not isinstance(profiles, list) or not 1 <= len(profiles) <= MAX_PROFILES:
        raise ValueError(f'interface library requires 1..{MAX_PROFILES} profiles')
    seen = set(); result = []
    for profile in profiles:
        pin = _pin(profile.get('sticker') if isinstance(profile,dict) else None)
        key = (pin['id'],pin['version'])
        if key in seen:
            raise ValueError('interface library has duplicate sticker profile')
        seen.add(key)
        definition = registry.get(*key) if registry is not None else None
        result.append(validate_profile(profile, definition))
    encode(value)
    return {'schema':PROFILE_LIBRARY,'profiles':result}


def port(profile, port_id):
    checked = validate_profile(profile)
    identifier(port_id)
    for item in checked['ports']:
        if item['id'] == port_id:
            return item
    raise ValueError('unknown named interface port')


def match_interfaces(a_profile, a_port, b_profile, b_port):
    a = port(a_profile,a_port); b = port(b_profile,b_port)
    if a['interface'] != b['interface']:
        raise ValueError('named ports use different interfaces')
    if not _compatible(a,b):
        raise ValueError('named port roles do not mutually accept each other')
    return {'schema':MATCH,'interface':a['interface'],
            'a':{'sticker':copy.deepcopy(a_profile['sticker']),'port':a['id'],'role':a['role']},
            'b':{'sticker':copy.deepcopy(b_profile['sticker']),'port':b['id'],'role':b['role']}}


class InterfaceCatalog:
    """Bounded registry-verified discovery over companion interface profiles.

    This is an in-memory authoring index, not a new persistent registry schema.
    Candidates prove declared interface/role compatibility only; no geometric fit
    or renderer quality is inferred.
    """
    def __init__(self, registry, profile_library):
        self.library = validate_profile_library(profile_library, registry)
        self._profiles = {(p['sticker']['id'],p['sticker']['version']):p
                          for p in self.library['profiles']}

    def profile(self,id,ver):
        identifier(id); version(ver)
        try:
            return copy.deepcopy(self._profiles[(id,ver)])
        except KeyError:
            raise ValueError('no named interface profile for sticker version') from None

    def compatible(self,id,ver,port_id,*,after=0,limit=30):
        if type(after) is not int or after < 0 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError('invalid interface search cursor/limit')
        source_profile=self.profile(id,ver); source=port(source_profile,port_id)
        entries=[]; cursor=0
        for candidate_profile in self.library['profiles']:
            for candidate in candidate_profile['ports']:
                cursor += 1
                if cursor <= after:
                    continue
                if _compatible(source,candidate):
                    entries.append({'sticker':copy.deepcopy(candidate_profile['sticker']),
                                    'port':candidate['id'],'interface':candidate['interface'],
                                    'role':candidate['role']})
                    if len(entries) == limit:
                        return {'source':{'sticker':copy.deepcopy(source_profile['sticker']),
                                          'port':source['id'],'interface':source['interface'],
                                          'role':source['role']},
                                'entries':entries,'next_cursor':cursor,'complete':False}
        return {'source':{'sticker':copy.deepcopy(source_profile['sticker']),
                          'port':source['id'],'interface':source['interface'],
                          'role':source['role']},
                'entries':entries,'next_cursor':cursor,'complete':True}


def mate_frame(host_profile, host_port, child_profile, child_port, *, host_frame=None):
    """Return the child-root frame that makes two named mating frames coincide."""
    match_interfaces(host_profile,host_port,child_profile,child_port)
    host = rigid(identity() if host_frame is None else host_frame)
    a = port(host_profile,host_port); b = port(child_profile,child_port)
    return rigid(multiply(multiply(host,a['frame']),inverse_rigid(b['frame'])))


def assembly_target(host_definition, host_profile, host_port,
                    child_definition, child_profile, child_port, *, host_frame=None):
    """Return an ordinary v1 assembly target derived from two named profiles.

    The resulting saved assembly remains standard sticker v1 data; the companion
    profiles are authoring evidence and are not required to replay that assembly.
    """
    host = validate(host_definition); child = validate(child_definition)
    validate_profile(host_profile,host); validate_profile(child_profile,child)
    if host['attachment']['space'] != '3d' or child['attachment']['space'] != '3d':
        raise ValueError('named rigid interface mating requires 3d stickers')
    return {'space':'3d','socket':child['attachment']['socket'],
            'frame':mate_frame(host_profile,host_port,child_profile,child_port,
                               host_frame=host_frame)}
