# Multi-occupancy experiment

Sticker Fabric 0.8.0 adds explicit, exact-pinned **occupancy slots** underneath
named rigid interface ports. The purpose is to model authoring cases where one
logical connection site intentionally hosts several children—such as a shaft with
a hub, wheel and detail disc—without turning named ports into silently reusable
capacity buckets.

## Why a companion layer

`axm.sticker/v1`, named-interface profiles and saved assembly schemas remain
unchanged. Occupancy is experimental authoring data pinned to exact sticker
versions.

A normal named port is still single-use in connection trees and closure sets.
Multi-occupancy is allowed only when an exact occupancy profile explicitly
publishes named slots below that port.

## Occupancy profiles

`axm.sticker-occupancy-profile/v0.1` contains:

- one exact sticker pin;
- one or more named interface ports on that sticker;
- a bounded set of named slots for each port;
- one rigid offset per slot, relative to the port's existing local mating frame.

The profile must match the exact Registry definition and exact named-interface
profile. A slot does not change interface or role semantics. The underlying host
port and child port must still pass the normal same-interface + mutual-role check.

Slots are unique within one host port and each slot may be consumed at most once
inside one occupancy plan.

## Occupancy plans

`axm.sticker-occupancy-plan/v0.1` contains:

- one existing exact-pinned connection-tree plan as the solved base;
- one or more new exact-pinned occupant instances;
- for each occupant: a base instance, host named port, occupancy slot and child
  named port.

In v0.1:

- occupancy hosts must be instances from the base plan;
- a host port already consumed by the base connection tree cannot also host
  occupancy slots;
- occupants cannot themselves become occupancy hosts;
- one slot can host only one occupant.

These boundaries keep the first experiment deterministic and prevent hidden
recursive capacity semantics.

## Solving

The base connection tree is solved first. For an occupant, the effective host
mating frame is:

`host_port_frame × slot_offset`

The occupant root frame is then:

`host_instance_frame × host_port_frame × slot_offset × inverse(child_port_frame)`

No geometry or collision query is involved. The slot offset is explicit authoring
data.

## Saving

`save_occupancy_plan` compiles the base instances and solved occupants into
ordinary `axm.sticker.assembly-3d/v1` children. The saved assembly therefore
replays without the occupancy profile or occupancy plan being present.

## Microforge proof

`tools/build_microforge_occupancy_examples.py` adds one exact occupancy profile to
the existing `micro-axle` sticker.

Both axle ends expose three declared slots. The positive end is used in the
reproducible example:

- `hub-seat` at the original named port frame;
- `wheel-seat` offset along local Y;
- `detail-seat` farther along local Y.

Three exact child instances—`micro-hub`, `micro-wheel` and `micro-disc`—all share
the same axle `positive` named port while consuming different slots. They still
pass the existing `micro-axle` role contract (`shaft` accepting `bearing`,
`wheel`, and `detail`).

This is the first evidence that one logical AXM connection point can expose
bounded deterministic capacity without weakening single-use semantics elsewhere.

## Truth boundary

Occupancy evidence proves only:

- the host and child exact sticker/profile identities;
- the declared named port and slot identities;
- the existing interface/role compatibility contract;
- deterministic rigid offsets for each occupied slot;
- unique slot consumption within the plan.

It does **not** prove that the stacked meshes fit, avoid overlap, have realistic
clearance, share a physical shaft correctly, preserve physics, support a load,
look good, or work in a target engine.

The Microforge offsets are authoring evidence, not mechanical dimensions.

## Future questions

This first version deliberately avoids:

- variable-capacity slots;
- dynamic insertion order;
- occupants hosting further occupants;
- slot ranges or continuous rails;
- automatic packing;
- geometry-derived spacing;
- combining occupancy with loop-solving adjustment.

Those should be separate experiments if repeated real builds demonstrate a need
and a deterministic contract can be stated without hiding decisions.
