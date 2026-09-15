#!/usr/bin/env python3
"""Build exact-pinned Microforge occupancy slots plus one stacked axle plan."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))

from axm_stickers.connections import PLAN
from axm_stickers.core import digest
from axm_stickers.interfaces import PROFILE_LIBRARY
from axm_stickers.occupancy import OCCUPANCY_LIBRARY, OCCUPANCY_PLAN, occupancy_profile
from axm_stickers.placement import identity
from build_microforge_interfaces import build_interfaces
from build_microforge_library import build_library


def frame(y=0):
    value=identity();value[7]=float(y);return value


def build_occupancy(library=None,interfaces=None):
    library=build_library() if library is None else library
    interfaces=build_interfaces(library) if interfaces is None else interfaces
    definitions={d['id']:d for d in library['definitions']}
    named={p['sticker']['id']:p for p in interfaces['profiles']}
    axle_profile=occupancy_profile(definitions['micro-axle'],named['micro-axle'],[
        {'port':'positive','slots':[
            {'id':'hub-seat','offset':frame(0)},
            {'id':'wheel-seat','offset':frame(.18)},
            {'id':'detail-seat','offset':frame(.31)},
        ]},
        {'port':'negative','slots':[
            {'id':'hub-seat','offset':frame(0)},
            {'id':'wheel-seat','offset':frame(-.18)},
            {'id':'detail-seat','offset':frame(-.31)},
        ]},
    ])
    occupancy_library={'schema':OCCUPANCY_LIBRARY,'profiles':[axle_profile]}
    def pin(sticker_id):
        d=definitions[sticker_id]
        return {'id':sticker_id,'version':d['version'],'digest':digest(d)}
    base={'schema':PLAN,'root':{'instance':'axle','frame':identity()},
          'instances':[{'id':'axle','sticker':pin('micro-axle')}],
          'connections':[]}
    plan={'schema':OCCUPANCY_PLAN,'base':base,'occupants':[
        {'id':'hub','sticker':pin('micro-hub'),
         'host':{'instance':'axle','port':'positive','slot':'hub-seat'},'port':'center'},
        {'id':'wheel','sticker':pin('micro-wheel'),
         'host':{'instance':'axle','port':'positive','slot':'wheel-seat'},'port':'center'},
        {'id':'detail','sticker':pin('micro-disc'),
         'host':{'instance':'axle','port':'positive','slot':'detail-seat'},'port':'center'},
    ]}
    return {'schema':'axm.microforge-occupancy-example/v0.1',
            'interface_schema':PROFILE_LIBRARY,
            'occupancy_library':occupancy_library,'plan':plan}


def main(argv=None):
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args(argv)
    value=build_occupancy();args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    profile=value['occupancy_library']['profiles'][0]
    print(json.dumps({'output':str(args.output),'occupants':len(value['plan']['occupants']),
                      'ports':len(profile['ports']),
                      'slots':sum(len(x['slots']) for x in profile['ports'])},sort_keys=True))

if __name__=='__main__':main()
