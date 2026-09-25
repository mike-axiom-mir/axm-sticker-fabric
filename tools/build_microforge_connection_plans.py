#!/usr/bin/env python3
"""Build reproducible Microforge named-port connection-plan examples."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))

from axm_stickers import digest, validate_connection_plan
from axm_stickers.connections import PLAN
from axm_stickers.placement import identity
from build_microforge_library import build_library

SCHEMA='axm.microforge-connection-plans/v0.1'


def build_plans(library=None):
    library=build_library() if library is None else library
    definitions={definition['id']:definition for definition in library['definitions']}
    def pin(sticker_id):
        definition=definitions[sticker_id]
        return {'id':sticker_id,'version':definition['version'],'digest':digest(definition)}
    def item(instance_id,sticker_id):
        return {'id':instance_id,'sticker':pin(sticker_id)}
    def endpoint(instance_id,port_id):
        return {'instance':instance_id,'port':port_id}
    def edge(a_instance,a_port,b_instance,b_port):
        return {'a':endpoint(a_instance,a_port),'b':endpoint(b_instance,b_port)}

    structural=validate_connection_plan({
        'schema':PLAN,
        'root':{'instance':'cube','frame':identity()},
        'instances':[
            item('cube','micro-cube'),
            item('beam','micro-beam'),
            item('column','micro-column'),
            item('cap','micro-cap'),
            item('plate','micro-plate'),
            item('pin','micro-pin'),
            item('marker','micro-marker'),
        ],
        'connections':[
            edge('cube','x-pos','beam','left'),
            edge('cube','y-pos','column','bottom'),
            edge('column','top','cap','base'),
            edge('cube','z-pos','plate','left-edge'),
            edge('plate','fastener-ne','pin','bottom'),
            edge('plate','marker-seat','marker','base'),
        ],
    })
    axle=validate_connection_plan({
        'schema':PLAN,
        'root':{'instance':'axle','frame':identity()},
        'instances':[
            item('axle','micro-axle'),
            item('hub','micro-hub'),
            item('wheel','micro-wheel'),
        ],
        'connections':[
            edge('axle','negative','hub','center'),
            edge('axle','positive','wheel','center'),
        ],
    })
    plans=[{'id':'microforge-structural-plan','plan':structural},
           {'id':'microforge-axle-plan','plan':axle}]
    return {'schema':SCHEMA,'plans':plans,
            'digests':{entry['id']:digest(entry['plan']) for entry in plans}}


def main(argv=None):
    parser=argparse.ArgumentParser(); parser.add_argument('output',type=Path)
    args=parser.parse_args(argv); value=build_plans()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output),'plans':len(value['plans']),
                      'digests':value['digests']},sort_keys=True))

if __name__=='__main__':main()
