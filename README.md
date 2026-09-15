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
`library_bundle`, `import_library`, `interface_compatible`,
`solve_connection_plan`, `save_connection_plan`, `verify_loop_closures`,
`save_closed_connection_plan`, `occupancy_slots`, `solve_occupancy_plan`, and
`save_occupancy_plan`. A saved group has immutable versions and exact child pins;
placement overrides never overwrite source. The registry stores shared source
bytes once, with author/license/source metadata, indexed discovery and atomic
portable import. No account is needed.

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

`search` can combine attachment `space`, adapter/socket, all-required `tags`,
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

## Microforge: small pieces into larger assets

```sh
python tools/build_microforge_library.py microforge-library.json
```

Microforge emits a real `axm.sticker-library/v1` bundle with 12 original rigid
GLB micro-parts, exact retained editable procedural JSON sources, three reusable
modules and one nested demo. The 16 definitions expand to 67 placed records while
shared source assets remain stored once by digest. See
[`docs/MICROFORGE_EVIDENCE.md`](docs/MICROFORGE_EVIDENCE.md).

## Experimental named interfaces

```sh
python tools/build_microforge_interfaces.py microforge-interfaces.json
```

`axm.sticker-interface-profile/v0.1` pins one exact sticker version and gives it
named rigid ports. Each port declares an interface, role, accepted peer roles and
local mating frame. A match requires same-interface + mutual-role acceptance;
tags alone are not compatibility evidence. `InterfaceCatalog` validates profiles
against the Registry and provides bounded compatible-port discovery. See
[`docs/NAMED_INTERFACES_EXPERIMENT.md`](docs/NAMED_INTERFACES_EXPERIMENT.md).

## Experimental connection plans

Sticker Fabric 0.6.0 grows named ports into bounded construction graphs.
`axm.sticker-connection-plan/v0.1` contains exact sticker instances, one explicit
root frame and one connected tree of named-port edges. The solver validates exact
Registry/profile/port evidence, propagates rigid transforms and compiles the
result to ordinary `axm.sticker.assembly-3d/v1` children.

```sh
python tools/build_microforge_connection_plans.py microforge-plans.json
```

See [`docs/CONNECTION_PLANS_EXPERIMENT.md`](docs/CONNECTION_PLANS_EXPERIMENT.md).

## Experimental loop closure

Sticker Fabric 0.7.0 keeps the tree as the only transform solver and adds loop
**verification**. `axm.sticker-closure-set/v0.1` adds extra named-port witnesses
with explicit translation and rotation-matrix tolerances. The witnesses never
move or optimize parts; they only report whether the already-solved tree satisfies
the extra constraints.

```sh
python tools/build_microforge_closure_examples.py microforge-loop.json
```

`save_closed_connection_plan` refuses to save a failed loop and otherwise saves
only the compiled v1 assembly. See
[`docs/LOOP_CLOSURE_EXPERIMENT.md`](docs/LOOP_CLOSURE_EXPERIMENT.md).

## Experimental multi-occupancy

Sticker Fabric 0.8.0 makes one logical named port shareable only through explicit,
exact-pinned **occupancy slots**. `axm.sticker-occupancy-profile/v0.1` attaches a
bounded set of named rigid slot offsets beneath one or more existing named ports.
The underlying interface/role compatibility rules still apply; slots add capacity,
not new compatibility semantics.

Each slot remains single-use. In the first plan format, occupancy hosts must be
base-tree instances, a port already consumed by the base tree cannot also host
occupancy slots, and occupants cannot recursively become new occupancy hosts.

```sh
python tools/build_microforge_occupancy_examples.py microforge-occupancy.json
```

The first Microforge proof uses one `micro-axle` `positive` port with three
explicit slots—hub, wheel and detail—and attaches exact `micro-hub`,
`micro-wheel` and `micro-disc` instances through distinct seats. The solved
result compiles to a normal v1 saved assembly with no hidden occupancy runtime
state.

`occupancy_slots` exposes the declared capacity to scripts/editors; the same JSON
CLI can solve and save occupancy plans. See
[`docs/MULTI_OCCUPANCY_EXPERIMENT.md`](docs/MULTI_OCCUPANCY_EXPERIMENT.md).

## What this seed contains

- Executable registry, parameter controls, placement math and dependency closure.
- Graph-aware discovery for reusable assembly/creative dependencies and reverse use.
- Deterministic Microforge authoring with retained exact editable source.
- Exact-pin named interfaces and registry-verified compatibility discovery.
- Named-port connection trees that compile into stable v1 saved assemblies.
- Loop-closure witnesses that verify extra rigid constraints without changing solved transforms.
- Explicit multi-occupancy slots for bounded shared-port capacity.
- Save groups, portable libraries, batch registration and machine/human JSON CLI.
- Standard-library tests and independent installed-package CI.
- Pinned upstream origin, license and file hashes in `UPSTREAM.json` / `NOTICE`.
- Original `examples/rivetwing-library.json`: 15 rigid part sources, saved wing/gear
  groups and the complete 272-placement animated assembly.

It does not contain a thousand finished sticker designs, a graphical editor,
mesh wrapping, automatic packing, geometry-derived fit, or an AI that invents
parts. Other programs can consume exported libraries locally. Add authored designs
with exact source/license metadata and keep reproducible evidence beside them.

## Development and continuity

Run `python -m unittest discover -s tests -v` after installation. UC remains the
initial source of this seed; changes here must be deliberately reviewed and
adopted by UC, never fetched into a live UC process automatically. Preserve
pinned formats and existing files. Store libraries, not one file per placement.

See `AGENTS.md` for the four-root merge gate and `UPSTREAM.json` for provenance.
