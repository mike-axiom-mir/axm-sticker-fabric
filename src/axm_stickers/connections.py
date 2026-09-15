"""Experimental named-port connection graphs compiled into ordinary v1 assemblies.

Connection plans are authoring data. They do not change sticker definitions or
saved assembly schemas. A bounded tree of exact sticker pins is solved from one
explicit root frame, then compiled to ordinary assembly child targets.
"""
import copy

from .assembly import save_assembly
from .core import digest, encode, identifier, instance, sha, version
from .interfaces import InterfaceCatalog, match_interfaces, mate_frame, port
from .placement import identity, rigid

PLAN = 'axm.sticker-connection-plan/v0.1'
SOLUTION = 'axm.sticker-connection-solution/v0.1'
MAX_INSTANCES = 1024


def _pin(value):
    if not isinstance(value,dict) or set(value) != {'id','version','digest'}:
        raise ValueError('connection-plan instance requires an exact sticker pin')
    identifier(value['id']); version(value['version']); sha(value['digest'])
    return {'id':value['id'],'version':value['version'],'digest':value['digest']}


def _endpoint(value):
    if not isinstance(value,dict) or set(value) != {'instance','port'}:
        raise ValueError('connection endpoint requires instance and port')
    return {'instance':identifier(value['instance']),'port':identifier(value['port'])}


def validate_connection_plan(plan):
    if not isinstance(plan,dict) or set(plan) != {'schema','root','instances','connections'}:
        raise ValueError('unsupported connection plan fields')
    if plan['schema'] != PLAN:
        raise ValueError('unsupported connection plan schema')
    instances=plan['instances']
    if not isinstance(instances,list) or not 1 <= len(instances) <= MAX_INSTANCES:
        raise ValueError(f'connection plan requires 1..{MAX_INSTANCES} instances')
    ids=set(); checked_instances=[]
    for item in instances:
        if not isinstance(item,dict) or set(item) != {'id','sticker'}:
            raise ValueError('connection-plan instance requires id and sticker')
        instance_id=identifier(item['id'])
        if instance_id in ids:
            raise ValueError('connection-plan instance ids must be unique')
        ids.add(instance_id)
        checked_instances.append({'id':instance_id,'sticker':_pin(item['sticker'])})
    root=plan['root']
    if not isinstance(root,dict) or set(root) != {'instance','frame'}:
        raise ValueError('connection plan root requires instance and frame')
    root_id=identifier(root['instance'])
    if root_id not in ids:
        raise ValueError('connection plan root instance is missing')
    checked_root={'instance':root_id,'frame':rigid(root['frame'])}
    connections=plan['connections']
    if not isinstance(connections,list) or len(connections) != len(instances)-1:
        raise ValueError('connection plan must be a tree with instances minus one connections')
    checked_connections=[]; used_ports=set(); adjacency={key:[] for key in ids}
    for index,item in enumerate(connections):
        if not isinstance(item,dict) or set(item) != {'a','b'}:
            raise ValueError('connection requires a and b endpoints')
        a=_endpoint(item['a']); b=_endpoint(item['b'])
        if a['instance'] not in ids or b['instance'] not in ids:
            raise ValueError('connection references unknown instance')
        if a['instance'] == b['instance']:
            raise ValueError('connection cannot join an instance to itself')
        for endpoint in (a,b):
            key=(endpoint['instance'],endpoint['port'])
            if key in used_ports:
                raise ValueError('named port may be used only once in a connection plan')
            used_ports.add(key)
        checked_connections.append({'a':a,'b':b})
        adjacency[a['instance']].append((index,b['instance']))
        adjacency[b['instance']].append((index,a['instance']))
    visited={root_id}; queue=[root_id]
    while queue:
        current=queue.pop(0)
        for _,other in adjacency[current]:
            if other not in visited:
                visited.add(other); queue.append(other)
    if visited != ids:
        raise ValueError('connection plan must be one connected tree')
    checked={'schema':PLAN,'root':checked_root,
             'instances':checked_instances,'connections':checked_connections}
    encode(checked)
    return checked


def _context(registry,profile_library,plan):
    checked=validate_connection_plan(plan)
    catalog=InterfaceCatalog(registry,profile_library)
    definitions={}; profiles={}
    for item in checked['instances']:
        pin=item['sticker']; definition=registry.get(pin['id'],pin['version'])
        expected={'id':definition['id'],'version':definition['version'],'digest':digest(definition)}
        if pin != expected:
            raise ValueError('connection-plan sticker pin does not match registry definition')
        profile=catalog.profile(pin['id'],pin['version'])
        if profile['sticker'] != pin:
            raise ValueError('connection-plan sticker pin does not match interface profile')
        definitions[item['id']]=definition; profiles[item['id']]=profile
    for connection in checked['connections']:
        for endpoint in (connection['a'],connection['b']):
            port(profiles[endpoint['instance']],endpoint['port'])
    return checked,catalog,definitions,profiles


def solve_connection_plan(registry,profile_library,plan):
    """Solve a bounded connection tree from one explicit root transform."""
    checked,_,_,profiles=_context(registry,profile_library,plan)
    adjacency={item['id']:[] for item in checked['instances']}
    for index,connection in enumerate(checked['connections']):
        a,b=connection['a'],connection['b']
        adjacency[a['instance']].append((index,a,b))
        adjacency[b['instance']].append((index,b,a))
    root=checked['root']['instance']; frames={root:checked['root']['frame']}; queue=[root]
    while queue:
        current=queue.pop(0)
        for _,here,other in adjacency[current]:
            if other['instance'] in frames:
                continue
            frames[other['instance']]=mate_frame(
                profiles[current],here['port'],profiles[other['instance']],other['port'],
                host_frame=frames[current])
            queue.append(other['instance'])
    evidence=[]
    for connection in checked['connections']:
        a,b=connection['a'],connection['b']
        matched=match_interfaces(profiles[a['instance']],a['port'],
                                 profiles[b['instance']],b['port'])
        evidence.append({'a':copy.deepcopy(a),'b':copy.deepcopy(b),
                         'interface':matched['interface']})
    result={'schema':SOLUTION,'plan_digest':digest(checked),
            'root':copy.deepcopy(checked['root']),
            'frames':[{'instance':item['id'],'frame':frames[item['id']]}
                      for item in checked['instances']],
            'connections':evidence}
    encode(result)
    return result


def compile_connection_plan(registry,profile_library,plan):
    """Compile authoring graph to ordinary v1 assembly children."""
    checked,_,definitions,_=_context(registry,profile_library,plan)
    solved=solve_connection_plan(registry,profile_library,checked)
    frames={item['instance']:item['frame'] for item in solved['frames']}
    children=[]
    for item in checked['instances']:
        definition=definitions[item['id']]
        children.append({'instance':instance(definition,item['id']),
                         'target':{'space':'3d','socket':definition['attachment']['socket'],
                                   'frame':frames[item['id']]},
                         'motion':None,'clip':None})
    return children


def save_connection_plan(registry,profile_library,plan,*,id,name,origin,ver=1,
                         socket='mount',anchor=None,tags=None):
    """Save the compiled result as a normal immutable assembly sticker."""
    children=compile_connection_plan(registry,profile_library,plan)
    return save_assembly(registry,id=id,name=name,children=children,origin=origin,
                         ver=ver,socket=socket,anchor=anchor or identity(),tags=tags)
