#!/usr/bin/env python3
"""Build an exact-pin Microforge loop-closure witness.

The base connection plan is still a tree. One additional named-port edge checks
whether the already solved tree lands back on the root within explicit tolerance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'tools'))

from axm_stickers.closures import CLOSURE_SET
from axm_stickers.connections import PLAN
from axm_stickers.core import digest
from axm_stickers.placement import identity
from build_microforge_library import build_library


def endpoint(instance,port):
    return {'instance':instance,'port':port}


def build_closure(library=None):
    library=build_library() if library is None else library
    definitions={definition['id']:definition for definition in library['definitions']}
    def pin(sticker_id):
        d=definitions[sticker_id]
        return {'id':sticker_id,'version':d['version'],'digest':digest(d)}
    plan={'schema':PLAN,'root':{'instance':'root-cube','frame':identity()},
          'instances':[
              {'id':'root-cube','sticker':pin('micro-cube')},
              {'id':'beam-out','sticker':pin('micro-beam')},
              {'id':'far-cube','sticker':pin('micro-cube')},
              {'id':'beam-return','sticker':pin('micro-beam')},
          ],
          'connections':[
              {'a':endpoint('root-cube','x-pos'),'b':endpoint('beam-out','left')},
              {'a':endpoint('beam-out','right'),'b':endpoint('far-cube','x-pos')},
              {'a':endpoint('far-cube','x-neg'),'b':endpoint('beam-return','right')},
          ]}
    return {'schema':CLOSURE_SET,'plan':plan,
            'closures':[{'a':endpoint('beam-return','left'),
                         'b':endpoint('root-cube','x-neg')}],
            'tolerance':{'translation':1e-12,'rotation':1e-12}}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('output',type=Path)
    args=parser.parse_args(argv)
    value=build_closure()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n',
                           encoding='utf-8')
    print(json.dumps({'output':str(args.output),'instances':len(value['plan']['instances']),
                      'tree_connections':len(value['plan']['connections']),
                      'closure_edges':len(value['closures'])},sort_keys=True))

if __name__=='__main__':main()
