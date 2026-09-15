#!/usr/bin/env python3
"""Build experimental named-interface profiles for the Microforge library.

The output is companion authoring data pinned to exact sticker v1 definitions.
It does not rewrite stickers or become a renderer/runtime requirement.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))

from axm_stickers.interfaces import PROFILE_LIBRARY, interface_profile
from build_microforge_library import build_library


def frame(x=0,y=0,z=0):
    return [1.0,0.0,0.0,float(x), 0.0,1.0,0.0,float(y),
            0.0,0.0,1.0,float(z), 0.0,0.0,0.0,1.0]


def named(id, interface, role, accepts, at):
    return {'id':id,'interface':interface,'role':role,'accepts':list(accepts),'frame':at}


def build_interfaces(library=None):
    library = build_library() if library is None else library
    definitions = {definition['id']:definition for definition in library['definitions']}
    structure_accepts=['structure','brace','finish']
    profiles=[]

    profiles.append(interface_profile(definitions['micro-cube'],[
        named('x-neg','micro-structure','structure',structure_accepts,frame(-.175,0,0)),
        named('x-pos','micro-structure','structure',structure_accepts,frame(.175,0,0)),
        named('y-neg','micro-structure','structure',structure_accepts,frame(0,-.175,0)),
        named('y-pos','micro-structure','structure',structure_accepts,frame(0,.175,0)),
        named('z-neg','micro-structure','structure',structure_accepts,frame(0,0,-.175)),
        named('z-pos','micro-structure','structure',structure_accepts,frame(0,0,.175)),
    ]))
    profiles.append(interface_profile(definitions['micro-beam'],[
        named('left','micro-structure','structure',structure_accepts,frame(-.75,0,0)),
        named('right','micro-structure','structure',structure_accepts,frame(.75,0,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-column'],[
        named('bottom','micro-structure','structure',structure_accepts,frame(0,-.60,0)),
        named('top','micro-structure','structure',structure_accepts,frame(0,.60,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-brace'],[
        named('left','micro-structure','brace',['structure'],frame(-.40,0,0)),
        named('right','micro-structure','brace',['structure'],frame(.40,0,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-cap'],[
        named('base','micro-structure','finish',['structure'],frame(0,-.14,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-plate'],[
        named('left-edge','micro-structure','structure',structure_accepts,frame(-.60,0,0)),
        named('right-edge','micro-structure','structure',structure_accepts,frame(.60,0,0)),
        named('fastener-nw','micro-fastener','panel',['fastener'],frame(-.45,.06,-.28)),
        named('fastener-ne','micro-fastener','panel',['fastener'],frame(.45,.06,-.28)),
        named('fastener-sw','micro-fastener','panel',['fastener'],frame(-.45,.06,.28)),
        named('fastener-se','micro-fastener','panel',['fastener'],frame(.45,.06,.28)),
        named('marker-seat','micro-marker','panel',['marker'],frame(0,.06,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-pin'],[
        named('bottom','micro-fastener','fastener',['panel'],frame(0,-.225,0)),
        named('top','micro-fastener','fastener',['panel'],frame(0,.225,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-marker'],[
        named('base','micro-marker','marker',['panel'],frame(0,-.16,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-axle'],[
        named('negative','micro-axle','shaft',['bearing','wheel','detail'],frame(0,-.45,0)),
        named('positive','micro-axle','shaft',['bearing','wheel','detail'],frame(0,.45,0)),
    ]))
    profiles.append(interface_profile(definitions['micro-hub'],[
        named('center','micro-axle','bearing',['shaft'],frame()),
    ]))
    profiles.append(interface_profile(definitions['micro-wheel'],[
        named('center','micro-axle','wheel',['shaft'],frame()),
    ]))
    profiles.append(interface_profile(definitions['micro-disc'],[
        named('center','micro-axle','detail',['shaft'],frame()),
    ]))
    return {'schema':PROFILE_LIBRARY,'profiles':profiles}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args(argv)
    value=build_interfaces()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(args.output),'profiles':len(value['profiles']),
                      'ports':sum(len(profile['ports']) for profile in value['profiles'])},sort_keys=True))

if __name__=='__main__':
    main()
