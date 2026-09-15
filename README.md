# AXM Sticker Fabric

Reusable creative parts and a portable registry for humans and machines.
Stickers may describe images, editable layer stacks, rigid 3D pieces or saved
assemblies. A group can be saved as a sticker and reused in a larger group.

**Universal Creation stays standalone.** UC includes its own compatible core
and 2D/3D creation adapters. This repository is an optional place to grow and
share the fabric and portable sticker libraries, never a required UC service.

## Use locally

```sh
python -m pip install .
axm-stickers parts.sqlite request.json
```

Requests are ordinary JSON, identical for human/script/AI callers. Operations:
`register`, `register_many`, `get`, `search`, `dependencies`, `dependents`,
`describe`, `stats`, `instance`, `bundle`, `import_bundle`, `save_assembly`,
`library_bundle`, `import_library`. A saved group has immutable versions and
exact child pins; placement overrides never overwrite source. The registry
stores shared source bytes once, with author/license/source metadata, indexed
discovery and atomic portable import. No account is needed.

The fabric interprets the common definition/assembly contract. Rendering belongs
to a consumer. UC's `axm-sticker-create` creates procedural 3D parts, captures
existing GLBs or editable Studio layers, saves nested groups, and exports actual
animated GLB assemblies. See [UC assembly authoring](https://github.com/mike-axiom-mir/axm-universal-creation/blob/main/docs/STICKER_ASSEMBLIES.md).

## Registry discovery

Registry v2 adds a deterministic composition index around the existing immutable
sticker definitions. The sticker schema remains `axm.sticker/v1`; portable
sticker/library bundle formats are unchanged. Existing v1 SQLite registries are
migrated in place by rebuilding only derived discovery data from their stored
immutable definitions.

`search` can now combine attachment `space`, adapter/socket, all-required `tags`,
`any_tags`, and an exact or id/version `depends_on` constraint. `dependencies`
reports direct assembly children and creative-task dependency pins together with
whether the pinned source is `exact`, `missing`, or a `digest_mismatch` in the
local registry. `dependents` walks the reverse edge so tools can discover which
saved groups or creative tasks reuse a part. `describe` returns bounded factual
metadata, parameter names, asset byte counts and direct dependency evidence;
`stats` gives a renderer-free registry inventory.

The index deliberately does not infer hidden relationships. Known assembly and
creative-task contracts report `indexed`; a malformed known contract reports
`malformed`; other adapters report `not_declared`. Those states describe what
the registry can prove, not the visual quality or semantic usefulness of a part.
See [`docs/REGISTRY_DISCOVERY.md`](docs/REGISTRY_DISCOVERY.md).

Example request:

```json
{
  "operation": "search",
  "space": "3d",
  "tags": ["mechanical", "metal"],
  "any_tags": ["hinge", "joint"],
  "limit": 30
}
```

## Microforge: small pieces into larger assets

The first dedicated small-part growth set is generated with only the Python
standard library:

```sh
python tools/build_microforge_library.py microforge-library.json
```

That emits a real `axm.sticker-library/v1` bundle with 12 original rigid GLB
micro-parts, each retaining its exact editable procedural JSON source, three
reusable saved modules, and one nested demo. The 16 definitions expand to 67
placed records while shared source assets remain stored once by digest.

The generated output is deliberately reproducible rather than checked in as a
second ~base64 copy of its binary sources. `examples/microforge-summary.json`
pins the expected root digest, IDs and counts, and CI regenerates/imports the
full library. See [`docs/MICROFORGE_EVIDENCE.md`](docs/MICROFORGE_EVIDENCE.md)
for what this exercise proves and the concrete v1 limits it exposed.

## What this seed contains

- Executable registry, parameter controls, placement math, dependency closure.
- Graph-aware discovery for reusable assembly/creative dependencies and reverse use.
- Deterministic Microforge authoring: 12 rigid micro-parts, three modules and a
  67-record nested composition with retained editable source.
- Save groups, portable libraries, batch registration and machine/human CLI.
- Standard-library tests and independent installed-package CI.
- Pinned upstream origin, license, and file hashes in `UPSTREAM.json` / `NOTICE`.
- Original `examples/rivetwing-library.json`: 15 rigid part sources, saved wing/gear
  groups and the complete 272-placement animated assembly.
  `examples/create-rivetwing.json` contains reproducible UC authoring requests.

It does not contain a thousand finished sticker designs, a graphical editor,
mesh wrapping, or an AI that invents parts. Other programs can consume exported
libraries locally. Add authored designs with exact source and license metadata;
keep tests/recipes alongside creations so improvements can be reproduced.

## Development and continuity

Run `python -m unittest discover -s tests -v` after installation. UC remains the
initial source of this seed; changes here must be deliberately reviewed and
adopted by UC, never fetched into a live UC process automatically. Preserve
pinned formats and existing files. Store libraries, not one file per placement.

See `AGENTS.md` for the four-root merge gate and `UPSTREAM.json` for provenance.

Import the shipped Rivetwing example with Python:

```python
import json
from axm_stickers import Registry
from axm_stickers.assembly import import_library
with Registry("parts.sqlite") as registry:
    import_library(registry, json.load(open("examples/rivetwing-library.json")))
```

Or generate Microforge and import the resulting JSON the same way. UC can consume
compatible libraries through `axm-sticker-create` without this registry becoming
a required UC service.
