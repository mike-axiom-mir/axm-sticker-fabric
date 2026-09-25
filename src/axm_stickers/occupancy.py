"""Explicit multi-occupancy slots layered above named rigid interface ports.

The base connection tree still solves the structure. A named host port becomes
shareable only through exact-pinned companion slots, and each slot remains
single-use. Saved output is still an ordinary sticker v1 assembly.
"""
import copy

from .assembly import save_assembly
from .connections import compile_connection_plan, solve_connection_plan, validate_connection_plan
from .core import digest, encode, identifier, instance, sha, version
from .interfaces import InterfaceCatalog, match_interfaces, port
from .placement import inverse_rigid, multiply, rigid

OCCUPANCY_PROFILE='axm.sticker-occupancy-profile/v0.1'
OCCUPANCY_LIBRARY='axm.sticker-occupancy-library/v0.1'
OCCUPANCY_PLAN='axm.sticker-occupancy-plan/v0.1'
OCCUPANCY_SOLUTION='axm.sticker-occupancy-solution/v0.1'
MAX_PORTS=64
MAX_SLOTS=64
MAX_PROFILES=4096
MAX_OCCUPANTS=1024


def _pin(value):
    if not isinstance(value,dict) or set(value) != {'id','version','digest'}:
        raise ValueError('occupancy data requires an exact sticker pin')
    identifier(value['id']); version(value['version']); sha(value['digest'])
    return {'id':value['id'],'version':value['version'],'digest':value['digest']}


def validate_occupancy_profile(value,definition=None,interface_profile=None):
    if not isinstance(value,dict) or set(value) != {'schema','sticker','ports'}:
        raise ValueError('unsupported occupancy-profile fields')
    if value['schema'] != OCCUPANCY_PROFILE: raise ValueError('unsupported occupancy-profile schema')
    pin=_pin(value['sticker']); entries=value['ports']
    if not isinstance(entries,list) or not 1 <= len(entries) <= MAX_PORTS:
        raise ValueError('occupancy profile requires 1..64 port entries')
    seen_ports=set(); checked=[]
    for entry in entries:
        if not isinstance(entry,dict) or set(entry) != {'port','slots'}:
            raise ValueError('occupancy port entry requires port and slots')
        port_id=identifier(entry['port'])
        if port_id in seen_ports: raise ValueError('occupancy profile ports must be unique')
        seen_ports.add(port_id); slots=entry['slots']
        if not isinstance(slots,list) or not 1 <= len(slots) <= MAX_SLOTS:
            raise ValueError('occupancy port requires 1..64 slots')
        seen_slots=set(); slot_values=[]
        for slot in slots:
            if not isinstance(slot,dict) or set(slot) != {'id','offset'}:
                raise ValueError('occupancy slot requires id and offset')
            slot_id=identifier(slot['id'])
            if slot_id in seen_slots: raise ValueError('occupancy slot ids must be unique per port')
            seen_slots.add(slot_id); slot_values.append({'id':slot_id,'offset':rigid(slot['offset'])})
        checked.append({'port':port_id,'slots':slot_values})
    if definition is not None:
        expected={'id':definition['id'],'version':definition['version'],'digest':digest(definition)}
        if pin != expected: raise ValueError('occupancy profile does not match exact sticker definition')
    if interface_profile is not None:
        if interface_profile['sticker'] != pin:
            raise ValueError('occupancy profile does not match exact interface profile')
        for entry in checked: port(interface_profile,entry['port'])
    result={'schema':OCCUPANCY_PROFILE,'sticker':pin,'ports':checked}; encode(result); return result


def validate_occupancy_library(value,registry=None,interface_library=None):
    if not isinstance(value,dict) or set(value) != {'schema','profiles'}:
        raise ValueError('unsupported occupancy-library fields')
    if value['schema'] != OCCUPANCY_LIBRARY: raise ValueError('unsupported occupancy-library schema')
    profiles=value['profiles']
    if not isinstance(profiles,list) or not 1 <= len(profiles) <= MAX_PROFILES:
        raise ValueError('occupancy library requires 1..4096 profiles')
    interfaces=InterfaceCatalog(registry,interface_library) if registry is not None and interface_library is not None else None
    seen=set(); checked=[]
    for value_profile in profiles:
        pin=_pin(value_profile.get('sticker') if isinstance(value_profile,dict) else None)
        key=(pin['id'],pin['version'])
        if key in seen: raise ValueError('occupancy library has duplicate sticker profile')
        seen.add(key)
        definition=registry.get(*key) if registry is not None else None
        named=interfaces.profile(*key) if interfaces is not None else None
        checked.append(validate_occupancy_profile(value_profile,definition,named))
    result={'schema':OCCUPANCY_LIBRARY,'profiles':checked}; encode(result); return result


def occupancy_profile(definition,interface_profile,ports):
    return validate_occupancy_profile({'schema':OCCUPANCY_PROFILE,
        'sticker':{'id':definition['id'],'version':definition['version'],'digest':digest(definition)},
        'ports':copy.deepcopy(ports)},definition,interface_profile)


def occupancy_slots(registry,interface_library,occupancy_library,id,ver,port_id):
    identifier(id); version(ver); identifier(port_id)
    checked=validate_occupancy_library(occupancy_library,registry,interface_library)
    for profile_value in checked['profiles']:
        if profile_value['sticker']['id']==id and profile_value['sticker']['version']==ver:
            for entry in profile_value['ports']:
                if entry['port']==port_id: return copy.deepcopy(entry['slots'])
            raise ValueError('named port has no occupancy slots')
    raise ValueError('no occupancy profile for exact sticker version')


def validate_occupancy_plan(value):
    if not isinstance(value,dict) or set(value) != {'schema','base','occupants'}:
        raise ValueError('unsupported occupancy-plan fields')
    if value['schema'] != OCCUPANCY_PLAN: raise ValueError('unsupported occupancy-plan schema')
    base=validate_connection_plan(value['base']); occupants=value['occupants']
    if not isinstance(occupants,list) or not 1 <= len(occupants) <= MAX_OCCUPANTS:
        raise ValueError('occupancy plan requires 1..1024 occupants')
    base_ids={x['id'] for x in base['instances']}
    base_used={(edge[side]['instance'],edge[side]['port']) for edge in base['connections'] for side in ('a','b')}
    ids=set(); slots=set(); checked=[]
    for item in occupants:
        if not isinstance(item,dict) or set(item) != {'id','sticker','host','port'}:
            raise ValueError('occupant requires id, sticker, host and port')
        occupant_id=identifier(item['id'])
        if occupant_id in base_ids or occupant_id in ids: raise ValueError('occupancy instance ids must be unique')
        ids.add(occupant_id); pin=_pin(item['sticker']); host=item['host']
        if not isinstance(host,dict) or set(host) != {'instance','port','slot'}:
            raise ValueError('occupancy host requires instance, port and slot')
        host_instance=identifier(host['instance']); host_port=identifier(host['port']); host_slot=identifier(host['slot'])
        if host_instance not in base_ids: raise ValueError('occupancy host must reference a base-plan instance')
        if (host_instance,host_port) in base_used: raise ValueError('occupancy host port is already consumed by base tree')
        key=(host_instance,host_port,host_slot)
        if key in slots: raise ValueError('occupancy slot may be consumed only once')
        slots.add(key)
        checked.append({'id':occupant_id,'sticker':pin,
                        'host':{'instance':host_instance,'port':host_port,'slot':host_slot},
                        'port':identifier(item['port'])})
    result={'schema':OCCUPANCY_PLAN,'base':base,'occupants':checked}; encode(result); return result


def _library_map(registry,interface_library,occupancy_library):
    checked=validate_occupancy_library(occupancy_library,registry,interface_library)
    return {(p['sticker']['id'],p['sticker']['version']):p for p in checked['profiles']}


def _slot(profile_value,port_id,slot_id):
    for entry in profile_value['ports']:
        if entry['port']==port_id:
            for slot_value in entry['slots']:
                if slot_value['id']==slot_id: return slot_value
            raise ValueError('unknown occupancy slot')
    raise ValueError('named port has no occupancy slots')


def solve_occupancy_plan(registry,interface_library,occupancy_library,plan):
    checked=validate_occupancy_plan(plan); named=InterfaceCatalog(registry,interface_library)
    occupied=_library_map(registry,interface_library,occupancy_library)
    base_solution=solve_connection_plan(registry,interface_library,checked['base'])
    frames={x['instance']:x['frame'] for x in base_solution['frames']}
    base_pins={x['id']:x['sticker'] for x in checked['base']['instances']}; solved=[]
    for item in checked['occupants']:
        child=registry.get(item['sticker']['id'],item['sticker']['version'])
        if item['sticker'] != {'id':child['id'],'version':child['version'],'digest':digest(child)}:
            raise ValueError('occupant sticker pin does not match registry definition')
        host=item['host']; host_pin=base_pins[host['instance']]
        host_named=named.profile(host_pin['id'],host_pin['version']); child_named=named.profile(child['id'],child['version'])
        host_port=port(host_named,host['port']); child_port=port(child_named,item['port'])
        matched=match_interfaces(host_named,host['port'],child_named,item['port'])
        try: profile_value=occupied[(host_pin['id'],host_pin['version'])]
        except KeyError: raise ValueError('no occupancy profile for exact host sticker') from None
        slot_value=_slot(profile_value,host['port'],host['slot'])
        effective=multiply(host_port['frame'],slot_value['offset'])
        child_frame=rigid(multiply(multiply(frames[host['instance']],effective),inverse_rigid(child_port['frame'])))
        frames[item['id']]=child_frame
        solved.append({'instance':item['id'],'frame':child_frame,'host':copy.deepcopy(host),'interface':matched['interface']})
    result={'schema':OCCUPANCY_SOLUTION,'base_plan_digest':base_solution['plan_digest'],
            'base_frames':copy.deepcopy(base_solution['frames']),'occupants':solved}
    encode(result); return result


def compile_occupancy_plan(registry,interface_library,occupancy_library,plan):
    checked=validate_occupancy_plan(plan)
    children=compile_connection_plan(registry,interface_library,checked['base'])
    solved=solve_occupancy_plan(registry,interface_library,occupancy_library,checked)
    frames={x['instance']:x['frame'] for x in solved['occupants']}
    for item in checked['occupants']:
        definition=registry.get(item['sticker']['id'],item['sticker']['version'])
        children.append({'instance':instance(definition,item['id']),
                         'target':{'space':'3d','socket':definition['attachment']['socket'],'frame':frames[item['id']]},
                         'motion':None,'clip':None})
    return children


def save_occupancy_plan(registry,interface_library,occupancy_library,plan,*,id,name,origin,
                        ver=1,socket='mount',anchor=None,tags=None):
    children=compile_occupancy_plan(registry,interface_library,occupancy_library,plan)
    return save_assembly(registry,id=id,name=name,children=children,origin=origin,
                         ver=ver,socket=socket,anchor=anchor,tags=tags)
