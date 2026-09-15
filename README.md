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
`register`, `register_many`, `get`, `search`, `instance`, `bundle`, `import_bundle`,
`save_assembly`, `library_bundle`, `import_library`. A saved group has immutable
versions and exact child pins; placement overrides never overwrite source.
The registry stores shared source bytes once, with author/license/source
metadata, indexed discovery and atomic portable import. No account is needed.

The fabric interprets the common definition/assembly contract. Rendering belongs
to a consumer. UC's `axm-sticker-create` creates procedural 3D parts, captures
existing GLBs or editable Studio layers, saves nested groups, and exports actual
animated GLB assemblies. See [UC assembly authoring](https://github.com/mike-axiom-mir/axm-universal-creation/blob/main/docs/STICKER_ASSEMBLIES.md).

## What this first seed contains

- Executable registry, parameter controls, placement math, dependency closure.
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

Import the shipped example with Python:

```python
import json
from axm_stickers import Registry
from axm_stickers.assembly import import_library
with Registry("parts.sqlite") as registry:
    import_library(registry, json.load(open("examples/rivetwing-library.json")))
```

Then UC can export it through `axm-sticker-create` without installing this repo.
