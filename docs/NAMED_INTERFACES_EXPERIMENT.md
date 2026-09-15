# Named interfaces experiment

This experiment tests whether reusable rigid stickers benefit from multiple named
connection anchors and machine-checkable connection roles **without** changing
`axm.sticker/v1`.

The experiment is deliberately a companion layer. Sticker definitions, registry
storage and portable sticker/library bundle schemas remain unchanged.

## Profile contract

An `axm.sticker-interface-profile/v0.1` contains:

- an exact `{id, version, digest}` sticker pin;
- 1..64 named ports;
- one exact `interface` identifier per port;
- one `role` identifier per port;
- 1..16 explicitly accepted peer roles;
- one rigid local mating frame per port.

The local frame is a **mating coordinate frame**, not a claimed surface normal.
Mating two ports means aligning those coordinate frames exactly.

Profiles are grouped in `axm.sticker-interface-library/v0.1`. A profile library
may be validated against a Registry so every profile is proven to match the exact
stored sticker version it names. One profile is allowed per exact sticker
id/version in a profile library.

## Compatibility rule

A match requires both:

1. the two ports declare the same `interface` identifier; and
2. each port's role appears in the other port's explicit `accepts` list.

That is intentionally stronger than tags. For example, two `shaft` ports using
the same interface do not automatically mate if shafts only accept `wheel`,
`bearing` or `detail` peers.

The contract does not define universal physical meaning for names such as
`structure`, `shaft`, `wheel`, `panel` or `fastener`. Their machine-checkable
meaning in v0.1 is the explicit compatibility graph declared by the profiles.
This avoids pretending that a vocabulary invented in one experiment is already a
universal ontology.

## Mating math

For a host object at `host_frame`, host port local frame `A`, and child port local
frame `B`, the child root frame is:

`host_frame × A × inverse(B)`

The result is an ordinary rigid frame. `assembly_target(...)` converts it into the
existing v1 assembly target shape using the child's existing attachment socket.
Once saved, that assembly contains the exact resulting target frame and replays
without requiring the experimental profile layer.

This is important for continuity: the experiment can improve authoring without
silently turning old assets or the runtime into dependents of a new format.

## Microforge testbed

`python tools/build_microforge_interfaces.py OUTPUT.json` generates profiles for
12 Microforge primitive stickers with 28 named ports. Examples include:

- `micro-cube`: six structural face ports;
- `micro-beam`: left/right structural ends;
- `micro-column`: top/bottom structural ends;
- `micro-brace`: left/right brace ends;
- `micro-plate`: structural edges, four fastener seats and one marker seat;
- `micro-pin`: top/bottom fastener ports;
- `micro-axle`: positive/negative shaft ends;
- `micro-hub`, `micro-wheel`, `micro-disc`: axle-center roles;
- `micro-marker`: marker base;
- `micro-cap`: finishing base.

The test suite validates the generated profiles against the exact generated
Microforge sticker definitions and exercises structural, fastener and axle role
matches. It also verifies that named-port mating can author a normal saved v1
assembly.

`examples/microforge-interface-summary.json` records the small inspectable counts
and example matches without duplicating generated profile data.

## Truth boundary

A successful match proves only the declared interface/role contract and exact
pin relationship. It does **not** prove:

- the meshes physically touch;
- collision clearance;
- load capacity or mechanical strength;
- physics/joint behavior;
- UV/material continuity;
- aesthetic quality;
- target-engine acceptance.

A port frame can also be badly authored while still being mathematically rigid.
Visual/geometric observers remain separate evidence sources.

## What this experiment can teach us

If repeated real libraries benefit from this layer, the useful concepts may later
justify promotion into a stronger portable contract. That decision should be
based on observed reuse, not on the fact that this prototype works.

Questions to measure next include:

- whether named ports belong inside future sticker definitions or should stay as
  independently versioned companion profiles;
- whether connection roles need richer capabilities than mutual acceptance;
- whether ports need explicit tolerances, geometry envelopes or joint behavior;
- how profile evolution should relate to immutable sticker versions;
- whether multiple profiles for different domains on the same exact sticker are
  useful enough to relax the one-profile-per-version experimental rule.
