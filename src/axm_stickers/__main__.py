"""Independent registry CLI: JSON in/out, no UC import or runtime needed."""
import argparse
import json
from pathlib import Path
from .core import Registry, instance
from .assembly import save_assembly, library_bundle, import_library
from .connections import save_connection_plan, solve_connection_plan
from .interfaces import InterfaceCatalog


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
                          'solve_connection_plan','save_connection_plan'}:
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
            result=solve_connection_plan(registry,request.pop('profile_library'),
                                         request.pop('plan'))
            if request: raise TypeError('unexpected solve_connection_plan arguments')
        elif operation=='save_connection_plan':
            profiles=request.pop('profile_library'); plan=request.pop('plan')
            result=save_connection_plan(registry,profiles,plan,**request)
        else:
            result = getattr(registry,operation)(**request)
    print(json.dumps(result,ensure_ascii=False,allow_nan=False))


if __name__ == '__main__': main()
