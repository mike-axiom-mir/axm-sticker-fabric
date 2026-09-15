"""Independent registry CLI: JSON in/out, no UC import or runtime needed."""
import argparse
import json
from pathlib import Path
from .core import Registry, instance
from .assembly import save_assembly, library_bundle, import_library
from .connections import save_connection_plan, solve_connection_plan
from .closures import save_closed_connection_plan, verify_loop_closures
from .interfaces import InterfaceCatalog
from .occupancy import occupancy_slots, save_occupancy_plan, solve_occupancy_plan


def main(argv=None):
    parser = argparse.ArgumentParser(description='Portable local sticker registry')
    parser.add_argument('database',type=Path)
    parser.add_argument('request',type=Path)
    args = parser.parse_args(argv)
    with args.request.open('rb') as handle: raw = handle.read(48*1024*1024+1)
    if len(raw) > 48*1024*1024: parser.error('request exceeds 48 MiB')
    request = json.loads(raw)
    if not isinstance(request,dict): parser.error('request must be an object')
    operation = request.pop('operation',None)
    if operation not in {'search','get','register','register_many','bundle','import_bundle',
                          'save_assembly','library_bundle','import_library','instance',
                          'dependencies','dependents','describe','stats','interface_compatible',
                          'solve_connection_plan','save_connection_plan','verify_loop_closures',
                          'save_closed_connection_plan','occupancy_slots','solve_occupancy_plan',
                          'save_occupancy_plan'}:
        parser.error('unknown operation')
    with Registry(args.database) as registry:
        functions={'save_assembly':save_assembly,'library_bundle':library_bundle,
                   'import_library':import_library}
        if operation in functions:
            result=functions[operation](registry,**request)
        elif operation=='instance':
            d=registry.get(request.pop('sticker_id'),request.pop('version'))
            result=instance(d,**request)
        elif operation=='interface_compatible':
            profiles=request.pop('profile_library')
            catalog=InterfaceCatalog(registry,profiles)
            result=catalog.compatible(request.pop('sticker_id'),request.pop('version'),
                                      request.pop('port_id'),**request)
        elif operation=='solve_connection_plan':
            result=solve_connection_plan(registry,request.pop('profile_library'),request.pop('plan'))
            if request: raise TypeError('unexpected solve_connection_plan arguments')
        elif operation=='save_connection_plan':
            profiles=request.pop('profile_library'); plan=request.pop('plan')
            result=save_connection_plan(registry,profiles,plan,**request)
        elif operation=='verify_loop_closures':
            profiles=request.pop('profile_library'); closure_set=request.pop('closure_set')
            if request: raise TypeError('unexpected verify_loop_closures arguments')
            result=verify_loop_closures(registry,profiles,closure_set)
        elif operation=='save_closed_connection_plan':
            profiles=request.pop('profile_library'); closure_set=request.pop('closure_set')
            result=save_closed_connection_plan(registry,profiles,closure_set,**request)
        elif operation=='occupancy_slots':
            result=occupancy_slots(registry,request.pop('profile_library'),
                                   request.pop('occupancy_library'),request.pop('sticker_id'),
                                   request.pop('version'),request.pop('port_id'))
            if request: raise TypeError('unexpected occupancy_slots arguments')
        elif operation=='solve_occupancy_plan':
            result=solve_occupancy_plan(registry,request.pop('profile_library'),
                                        request.pop('occupancy_library'),request.pop('plan'))
            if request: raise TypeError('unexpected solve_occupancy_plan arguments')
        elif operation=='save_occupancy_plan':
            profiles=request.pop('profile_library'); occupancies=request.pop('occupancy_library')
            plan=request.pop('plan')
            result=save_occupancy_plan(registry,profiles,occupancies,plan,**request)
        else:
            result = getattr(registry,operation)(**request)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__ == '__main__': main()
