"""Loop-closure evidence layered above deterministic named-port connection trees.

The tree remains the only transform solver. Extra closure edges never move parts;
they independently predict already-solved frames and report bounded residuals.
Passing closure therefore means the declared rigid interface constraints agree,
not that meshes, physics, strength, clearance or aesthetics are valid.
"""
import copy
import math

from .connections import solve_connection_plan, validate_connection_plan, save_connection_plan
from .core import encode, identifier
from .interfaces import InterfaceCatalog, match_interfaces, mate_frame, port

CLOSURE_SET = 'axm.sticker-closure-set/v0.1'
CLOSURE_REPORT = 'axm.sticker-closure-report/v0.1'
MAX_CLOSURES = 1024


def _endpoint(value):
    if not isinstance(value,dict) or set(value) != {'instance','port'}:
        raise ValueError('closure endpoint requires instance and port')
    return {'instance':identifier(value['instance']),'port':identifier(value['port'])}


def _tolerance(value):
    if not isinstance(value,dict) or set(value) != {'translation','rotation'}:
        raise ValueError('closure tolerance requires translation and rotation')
    translation=value['translation']; rotation=value['rotation']
    if (type(translation) not in (int,float) or not math.isfinite(translation) or
            not 0 <= translation <= 1e6):
        raise ValueError('closure translation tolerance must be finite in 0..1e6')
    if (type(rotation) not in (int,float) or not math.isfinite(rotation) or
            not 0 <= rotation <= 2):
        raise ValueError('closure rotation tolerance must be finite in 0..2')
    return {'translation':float(translation),'rotation':float(rotation)}


def validate_closure_set(value):
    if not isinstance(value,dict) or set(value) != {'schema','plan','closures','tolerance'}:
        raise ValueError('unsupported closure-set fields')
    if value['schema'] != CLOSURE_SET:
        raise ValueError('unsupported closure-set schema')
    plan=validate_connection_plan(value['plan'])
    closures=value['closures']
    if not isinstance(closures,list) or not 1 <= len(closures) <= MAX_CLOSURES:
        raise ValueError(f'closure set requires 1..{MAX_CLOSURES} closure edges')
    ids={item['id'] for item in plan['instances']}
    occupied={(edge[side]['instance'],edge[side]['port'])
              for edge in plan['connections'] for side in ('a','b')}
    checked=[]
    for item in closures:
        if not isinstance(item,dict) or set(item) != {'a','b'}:
            raise ValueError('closure edge requires a and b endpoints')
        a=_endpoint(item['a']); b=_endpoint(item['b'])
        if a['instance'] not in ids or b['instance'] not in ids:
            raise ValueError('closure edge references unknown instance')
        if a['instance'] == b['instance']:
            raise ValueError('closure edge cannot join an instance to itself')
        for endpoint in (a,b):
            key=(endpoint['instance'],endpoint['port'])
            if key in occupied:
                raise ValueError('named port may be used only once across tree and closure edges')
            occupied.add(key)
        checked.append({'a':a,'b':b})
    result={'schema':CLOSURE_SET,'plan':plan,'closures':checked,
            'tolerance':_tolerance(value['tolerance'])}
    encode(result)
    return result


def _residual(expected,actual):
    translation=max(abs(expected[index]-actual[index]) for index in (3,7,11))
    rotation=max(abs(expected[row*4+column]-actual[row*4+column])
                 for row in range(3) for column in range(3))
    return {'translation':translation,'rotation':rotation}


def verify_loop_closures(registry,profile_library,value):
    """Verify extra loop edges against one already-solved tree, without adjustment."""
    checked=validate_closure_set(value)
    solved=solve_connection_plan(registry,profile_library,checked['plan'])
    frames={entry['instance']:entry['frame'] for entry in solved['frames']}
    pins={item['id']:item['sticker'] for item in checked['plan']['instances']}
    catalog=InterfaceCatalog(registry,profile_library)
    profiles={instance_id:catalog.profile(pin['id'],pin['version'])
              for instance_id,pin in pins.items()}
    entries=[]; tolerance=checked['tolerance']
    for edge in checked['closures']:
        a,b=edge['a'],edge['b']
        port(profiles[a['instance']],a['port']); port(profiles[b['instance']],b['port'])
        matched=match_interfaces(profiles[a['instance']],a['port'],
                                 profiles[b['instance']],b['port'])
        predicted_b=mate_frame(profiles[a['instance']],a['port'],
                               profiles[b['instance']],b['port'],
                               host_frame=frames[a['instance']])
        predicted_a=mate_frame(profiles[b['instance']],b['port'],
                               profiles[a['instance']],a['port'],
                               host_frame=frames[b['instance']])
        forward=_residual(predicted_b,frames[b['instance']])
        reverse=_residual(predicted_a,frames[a['instance']])
        residual={'translation':max(forward['translation'],reverse['translation']),
                  'rotation':max(forward['rotation'],reverse['rotation'])}
        closed=(residual['translation'] <= tolerance['translation'] and
                residual['rotation'] <= tolerance['rotation'])
        entries.append({'a':copy.deepcopy(a),'b':copy.deepcopy(b),
                        'interface':matched['interface'],'closed':closed,
                        'residual':residual})
    report={'schema':CLOSURE_REPORT,'plan_digest':solved['plan_digest'],
            'tolerance':copy.deepcopy(tolerance),'all_closed':all(x['closed'] for x in entries),
            'closures':entries}
    encode(report)
    return report


def save_closed_connection_plan(registry,profile_library,value,*,id,name,origin,ver=1,
                                socket='mount',anchor=None,tags=None):
    """Save only when every declared loop closure passes; output remains sticker v1."""
    report=verify_loop_closures(registry,profile_library,value)
    if not report['all_closed']:
        raise ValueError('connection loop does not close within declared tolerance')
    return save_connection_plan(registry,profile_library,value['plan'],id=id,name=name,
                                origin=origin,ver=ver,socket=socket,anchor=anchor,tags=tags)
