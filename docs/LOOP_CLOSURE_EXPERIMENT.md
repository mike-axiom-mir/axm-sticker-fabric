# Loop closure experiment

Sticker Fabric 0.7.0 adds a bounded loop-closure evidence layer above the
existing named-port connection-tree solver. The tree remains the only mechanism
that determines transforms. Extra closure edges are **witnesses**: they are not
allowed to move or optimize any instance.

This separation matters. A tree always has one deterministic rigid solution from
one explicit root frame. A loop adds another constraint. Rather than introducing
an opaque numerical optimizer, v0.1 asks whether that additional constraint is
already satisfied by the solved tree.

## Companion format

`axm.sticker-closure-set/v0.1` contains:

- one existing `axm.sticker-connection-plan/v0.1` tree;
- one or more additional named-port closure edges;
- explicit translation and rotation-matrix tolerances.

The closure format does not modify `axm.sticker/v1`, interface profiles, Registry
storage, portable sticker bundles or saved assembly schemas.

Every closure endpoint must:

- reference an instance already present in the tree plan;
- reference a named port that exists on its exact interface profile;
- remain single-use across both the tree and all closure edges;
- satisfy the same-interface + mutual-role compatibility rule.

## Verification

The base tree is solved normally. For each closure edge A.port -> B.port, the
checker independently predicts B's root frame from A's already solved frame:

`predicted_B = frame_A × port_A × inverse(port_B)`

It also performs the reverse prediction from B back to A. The report keeps the
maximum forward/reverse residual for:

- translation: maximum absolute difference of X/Y/Z translation components;
- rotation: maximum absolute difference across the 3x3 rotation matrix.

The edge is `closed` only when both residuals are within the caller-declared
bounds. `all_closed` is true only when every closure witness passes.

No averaging, snapping, least-squares fitting or hidden adjustment occurs. A bad
loop stays bad and exposes its residual.

## Saving

`save_closed_connection_plan` first requires all closure witnesses to pass. It
then compiles only the underlying solved tree into an ordinary immutable
`axm.sticker.assembly-3d/v1` definition.

The saved result therefore replays without requiring the experimental closure or
interface-profile layers. The closure evidence remains authoring/verification
evidence rather than a hidden runtime dependency.

## Microforge witness

`tools/build_microforge_closure_examples.py` builds one reproducible four-instance
loop witness using only existing Microforge parts:

1. root cube `x-pos` -> outbound beam `left`;
2. outbound beam `right` -> far cube `x-pos`;
3. far cube `x-neg` -> return beam `right`;
4. closure witness: return beam `left` -> root cube `x-neg`.

The first three edges form the deterministic tree. The fourth does not solve
anything; it checks whether the return beam independently lands back on the
unused opposite root-cube face.

This example is intentionally topological/transform evidence. The two beams may
occupy overlapping geometry. Passing the closure therefore does **not** claim a
physically usable frame.

## Truth boundary

A passing closure proves only:

- exact sticker/profile identity was present;
- the declared tree topology solved deterministically;
- the additional named interfaces were mutually compatible;
- the already solved rigid frames satisfy the additional connection within the
  declared numeric tolerance.

It does **not** prove mesh contact, non-intersection, clearance, strength,
manufacturability, joint freedom, physics stability, UV/material continuity,
aesthetics or target-engine acceptance.

## What remains unknown

This experiment deliberately does not solve an inconsistent loop. Future work
may investigate bounded adjustment or loop solving, but only if the objective,
degrees of freedom, tolerances, determinism and failure evidence can be made
explicit.

Multi-occupancy is also still outside this contract. A named port remains
single-use even in a closure set. Shared shafts, stacked washers and multiple
attachments to one interface remain a separate evidence-backed experiment.
