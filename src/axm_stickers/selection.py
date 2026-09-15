"""Extract exact pieces from a saved 3D assembly and save them as a new sticker.

Selection is structural evidence, not screenshot/mesh inference. Source instance
paths are exact, transforms are rebased around one selected pivot, and saved
output remains an ordinary immutable sticker v1 assembly.
"""
import copy

from .assembly import ASSEMBLY, MAX_DEPTH, MAX_PARTS, save_assembly
from .core import digest, encode, identifier, instance, resolve, sha, version
from .interfaces import InterfaceCatalog, interface_profile, port
from .placement import attachment_matrix, identity, inverse_rigid, multiply, rigid

SELECTION='axm.sticker-selection/v0.1'
EXTRACT='axm.sticker-selection-extract/v0.1'
SAVE='axm.sticker-selection-save/v0.1'
MAX_SELECTED=1024
MAX_EXPOSED=64


def _pin(value):
    if not isinstance(value,dict) or set(value) != {'id','version','digest'}:
        raise ValueError('selection requires an exact source sticker pin')
    identifier(value['id']); version(value['version']); sha(value['digest'])
    return {'id':value['id'],'version':value['version'],'digest':value['digest']}


def _path(value):
    if not isinstance(value,str) or len(value)>1024:
        raise ValueError('selection path must be bounded text')
    parts=value.split('/')
    if not 2 <= len(parts) <= MAX_DEPTH+1 or parts[0] != 'root':
        raise ValueError('selection path must address a non-root assembly instance')
    for part in parts[1:]: identifier(part)
    return value


def validate_selection(value):
    if not isinstance(value,dict) or set(value) != {'schema','source','paths','anchor'}:
        raise ValueError('selection requires schema, source, paths and anchor')
    if value['schema'] != SELECTION: raise ValueError('unsupported selection schema')
    source=_pin(value['source']); paths=value['paths']
    if not isinstance(paths,list) or not 1 <= len(paths) <= MAX_SELECTED:
        raise ValueError(f'selection requires 1..{MAX_SELECTED} paths')
    checked=sorted(_path(path) for path in paths)
    if len(checked) != len(set(checked)): raise ValueError('selection paths must be unique')
    anchor=_path(value['anchor'])
    if anchor not in checked: raise ValueError('selection anchor must be one selected path')
    for index,path in enumerate(checked):
        for other in checked[index+1:]:
            if other.startswith(path+'/'):
                raise ValueError('selection cannot contain both an ancestor and its descendant')
    result={'schema':SELECTION,'source':source,'paths':checked,'anchor':anchor}
    encode(result); return result


def _scale(placed): return placed.get('placement',{}).get('scale',1)


def _addressable(registry,root):
    """Return addressable records with target/local transforms in root coordinates."""
    records={}; blocked=[]; count=0
    def visit(definition,placed,parent_frame,path,ancestors):
        nonlocal count
        if len(ancestors) >= MAX_DEPTH or count >= MAX_PARTS:
            raise ValueError('selection traversal budget exceeded')
        recipe=resolve(definition,placed)
        if definition['adapter'] != ASSEMBLY: return
        if set(recipe) != {'children'} or not isinstance(recipe['children'],list):
            raise ValueError('selection source assembly is malformed')
        for child in recipe['children']:
            if not isinstance(child,dict) or set(child) != {'instance','target','motion','clip'}:
                raise ValueError('selection source has malformed child')
            placed_child=child['instance']; pin=placed_child.get('sticker',{})
            child_definition=registry.get(pin.get('id'),pin.get('version'))
            resolve(child_definition,placed_child)
            child_digest=digest(child_definition)
            if child_digest in ancestors: raise ValueError('cyclic selection source assembly')
            child_path=path+'/'+identifier(placed_child.get('id'))
            target=child['target']
            if not isinstance(target,dict) or set(target) != {'space','socket','frame'} or target['space']!='3d':
                raise ValueError('selection v0.1 requires rigid 3d assembly targets')
            target_world=rigid(multiply(parent_frame,rigid(target['frame'])))
            local_parent=attachment_matrix(child_definition,placed_child,target)
            local_world=multiply(parent_frame,local_parent)
            count+=1
            records[child_path]={'path':child_path,'definition':child_definition,
                                 'instance':copy.deepcopy(placed_child),'target_world':target_world,
                                 'local_world':local_world,'motion':copy.deepcopy(child['motion']),
                                 'clip':child['clip'],'parent_frame':copy.deepcopy(parent_frame)}
            if child_definition['adapter']==ASSEMBLY:
                if _scale(placed_child) != 1: blocked.append(child_path)
                else: visit(child_definition,placed_child,rigid(local_world),child_path,
                            ancestors+(child_digest,))
    visit(root,instance(root,'root'),identity(),'root',(digest(root),))
    return records,blocked


def selection_manifest(registry,source):
    pin=_pin(source); root=registry.get(pin['id'],pin['version'])
    if pin != {'id':root['id'],'version':root['version'],'digest':digest(root)}:
        raise ValueError('selection source pin does not match registry definition')
    if root['adapter'] != ASSEMBLY or root['attachment']['space'] != '3d':
        raise ValueError('selection v0.1 requires a saved 3d assembly source')
    records,blocked=_addressable(registry,root)
    return {'schema':'axm.sticker-selection-manifest/v0.1','source':pin,
            'entries':[{'path':path,'sticker':copy.deepcopy(record['instance']['sticker']),
                        'name':record['definition']['name'],'adapter':record['definition']['adapter']}
                       for path,record in sorted(records.items())],
            'blocked_descendants':blocked}


def _child_id(path,record,counts,index):
    original=record['instance']['id']
    if counts[original] == 1: return original
    suffix=digest({'path':path})[:8]; base=original[:62]
    return identifier(f'{base}-copy-{index:03d}-{suffix}')


def _rebase_motion(motion,parent_frame,rebase):
    if motion is None: return None
    result=[]
    for sample in motion:
        value=copy.deepcopy(sample)
        value['frame']=rigid(multiply(rebase,multiply(parent_frame,rigid(sample['frame']))))
        result.append(value)
    return result


def extract_selection(registry,selection):
    checked=validate_selection(selection); pin=checked['source']
    root=registry.get(pin['id'],pin['version'])
    if pin != {'id':root['id'],'version':root['version'],'digest':digest(root)}:
        raise ValueError('selection source pin does not match registry definition')
    if root['adapter'] != ASSEMBLY or root['attachment']['space'] != '3d':
        raise ValueError('selection v0.1 requires a saved 3d assembly source')
    records,blocked=_addressable(registry,root)
    for path in checked['paths']:
        if path not in records:
            if any(path.startswith(prefix+'/') for prefix in blocked):
                raise ValueError('selection cannot flatten through a scaled assembly ancestor')
            raise ValueError('selection path does not exist in source assembly')
    rebase=inverse_rigid(records[checked['anchor']]['target_world'])
    originals=[records[path]['instance']['id'] for path in checked['paths']]
    counts={value:originals.count(value) for value in set(originals)}
    children=[]; items=[]
    for index,path in enumerate(checked['paths'],1):
        record=records[path]; placed=copy.deepcopy(record['instance'])
        placed['id']=_child_id(path,record,counts,index)
        target={'space':'3d','socket':record['definition']['attachment']['socket'],
                'frame':rigid(multiply(rebase,record['target_world']))}
        motion=_rebase_motion(record['motion'],record['parent_frame'],rebase)
        children.append({'instance':placed,'target':target,'motion':motion,'clip':record['clip']})
        items.append({'path':path,'saved_instance':placed['id'],'sticker':copy.deepcopy(placed['sticker']),
                      'target':copy.deepcopy(target)})
    result={'schema':EXTRACT,'source':copy.deepcopy(pin),'selection_digest':digest(checked),
            'anchor':checked['anchor'],'items':items,'children':children}
    encode(result); return result


def _exposed_profile(registry,interface_library,selection,saved_definition,expose):
    if not isinstance(expose,list) or not 1 <= len(expose) <= MAX_EXPOSED:
        raise ValueError(f'expose requires 1..{MAX_EXPOSED} named ports')
    checked=validate_selection(selection); root=registry.get(checked['source']['id'],checked['source']['version'])
    records,_=_addressable(registry,root); catalog=InterfaceCatalog(registry,interface_library)
    anchor_inverse=inverse_rigid(records[checked['anchor']]['target_world']); result=[]; ids=set()
    for item in expose:
        if not isinstance(item,dict) or set(item) != {'path','port','id'}:
            raise ValueError('exposed port requires path, port and id')
        path=_path(item['path'])
        if path not in checked['paths']: raise ValueError('exposed port must belong to selected path')
        new_id=identifier(item['id'])
        if new_id in ids: raise ValueError('exposed port ids must be unique')
        ids.add(new_id); record=records[path]
        if _scale(record['instance']) != 1:
            raise ValueError('cannot expose a rigid port from a scaled selected instance')
        source_profile=catalog.profile(record['definition']['id'],record['definition']['version'])
        source_port=port(source_profile,identifier(item['port']))
        local_world=rigid(record['local_world'])
        frame=rigid(multiply(anchor_inverse,multiply(local_world,source_port['frame'])))
        result.append({'id':new_id,'interface':source_port['interface'],'role':source_port['role'],
                       'accepts':copy.deepcopy(source_port['accepts']),'frame':frame})
    return interface_profile(saved_definition,result)


def save_selection_as_sticker(registry,selection,*,id,name,author,license,ver=1,
                              socket='mount',tags=None,interface_library=None,expose=None):
    checked=validate_selection(selection); extracted=extract_selection(registry,checked)
    source=checked['source']
    origin={'author':author,'license':license,
            'source':f"Selection {extracted['selection_digest']} from {source['id']}@{source['version']} sha256:{source['digest']}"}
    saved=save_assembly(registry,id=id,name=name,children=extracted['children'],origin=origin,
                        ver=ver,socket=socket,anchor=identity(),tags=tags)
    profile=None
    if expose is not None:
        if interface_library is None: raise ValueError('exposed ports require an interface library')
        profile=_exposed_profile(registry,interface_library,checked,saved,expose)
    result={'schema':SAVE,'sticker':saved,
            'receipt':{'source':copy.deepcopy(source),'selection_digest':extracted['selection_digest'],
                       'anchor':checked['anchor'],'items':copy.deepcopy(extracted['items'])},
            'interface_profile':profile}
    encode(result); return result
