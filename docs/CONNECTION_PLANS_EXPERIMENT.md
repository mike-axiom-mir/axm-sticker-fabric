# Connection-plan experiment

Sticker Fabric 0.6.0 adds a bounded authoring experiment above the existing
immutable sticker v1, saved-assembly v1 and named-interface v0.1 contracts.
Nothing in this wave changes a sticker definition or the portable library format.

The purpose is to test a stronger question than pairwise mating:

> Can a human or machine describe a small object as a graph of exact reusable
> parts and named connections, then deterministically compile that graph into a
> normal saved v1 assembly?

## Connection plan

`axm.sticker-connection-plan/v0.1` contains:

- `instances`: 1..1024 unique authoring instance IDs, each with an exact
  `{id, version, digest}` sticker pin;
- `root`: one instance ID plus an explicit rigid world frame;
- `connections`: exactly `instances - 1` named-port edges.

The first experiment deliberately requires the graph to be one connected tree.
Every endpoint names one instance and one named interface port. A named port may
be consumed only once inside a plan.

Those restrictions are not claims that every useful future object is a tree.
They remove loop-closure ambiguity and multi-occupancy semantics from the first
solver so evidence stays easy to inspect.

## Registry-backed compatibility catalog

`InterfaceCatalog` validates a companion interface library against the current
Registry and offers bounded paginated compatibility discovery. A query starts
from an exact registered sticker version and named port, then returns exact
profile pins/ports that satisfy:

1. the same declared interface; and
2. mutual role acceptance.

Search does not infer fit from tag similarity, names, geometry, visual appearance
or model knowledge. It does not render or load GLB geometry.

## Solving

`solve_connection_plan(registry, profiles, plan)` validates:

- graph shape and bounds;
- unique instance IDs;
- single use of every named port;
- exact plan pins against current Registry definitions;
- exact profile pins against those same definitions;
- existence of every named port;
- interface and mutual-role compatibility for every connection.

One explicit root frame is fixed. The tree is traversed outward. For each edge,
the unsolved instance transform is computed from the already solved instance:

`known_instance_frame × known_port_frame × inverse(new_port_frame)`

The result is `axm.sticker-connection-solution/v0.1`: one deterministic root
frame per instance plus per-edge interface evidence and the exact plan digest.

## Compilation boundary

`compile_connection_plan(...)` turns every solved instance into an ordinary v1
assembly child with its exact sticker pin and solved rigid target frame.

`save_connection_plan(...)` then uses the existing `save_assembly` path. The
saved object is therefore a normal immutable `axm.sticker/v1` using
`axm.sticker.assembly-3d/v1`.

The connection plan and interface profiles are **not required to replay that
saved assembly**. This is intentional: richer experimental authoring vocabulary
can be tested without silently making the stable runtime dependent on it.

## Microforge evidence

`tools/build_microforge_connection_plans.py` generates two reproducible plans:

### Structural plan

Seven exact instances:

- cube
- beam
- column
- cap
- plate
- pin
- marker

Six named connections exercise structural, finish, fastener and marker roles.
The cube is the explicit root.

### Axle plan

Three exact instances:

- axle
- hub
- wheel

Two named connections exercise shaft/bearing and shaft/wheel compatibility.

The tests solve these plans against the actual generated Microforge library and
its exact companion profile library.

## Current truth boundary

A valid solved graph proves only:

- exact source/version/profile identity;
- the declared tree topology;
- single-use named ports;
- declared interface and mutual-role compatibility;
- deterministic rigid-frame propagation;
- successful compilation into the existing v1 assembly contract.

It does **not** prove:

- meshes touch at the intended surfaces;
- parts do not overlap;
- collision clearance;
- physical strength or load transfer;
- hinge/axle/joint dynamics;
- UV or material continuity;
- visual quality;
- usefulness of the role vocabulary outside the tested authoring set;
- target-engine acceptance.

## New pressure exposed by the graph experiment

The tree restriction makes two likely future questions concrete:

1. **Loop closure.** Real frames, cages and mechanisms may intentionally connect
   a part through multiple paths. Supporting this requires a deterministic
   consistency/error contract rather than simply accepting graph cycles.
2. **Port occupancy.** A shaft often carries several coaxial parts. The current
   single-use rule intentionally rejects that. A future experiment needs explicit
   occupancy/stacking semantics instead of silently allowing unlimited reuse of
   the same named port.

These are experiment candidates, not schema changes. The existing v1 formats
remain the stable compilation target.
