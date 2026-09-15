# Selection capture experiment — Sticker Fabric 0.9

Sticker Fabric 0.9 tests a simple authoring idea: take a structurally known part of a larger saved design and save that selected group as a reusable sticker.

This is deliberately **not** screenshot cropping, mesh segmentation, visual recognition, or an AI guessing what a user meant. The first contract operates on an exact saved 3D assembly already present in the Registry.

## Exact selection contract

`axm.sticker-selection/v0.1` contains:

- an exact source sticker pin (`id`, `version`, `digest`);
- one or more exact instance paths such as `root/corner-0/beam-x`;
- one selected path used as the new local pivot.

Paths are resolved through the saved assembly hierarchy. The source pin must still match the immutable Registry definition when the selection is previewed or saved.

A selection cannot include both an ancestor and one of its descendants. That avoids silently copying the same nested content twice.

## Rebase instead of bake

The selected parts keep their original exact sticker pins and instance data. Sticker Fabric computes their rigid target frames in source-root coordinates and rebases them around the chosen selected pivot.

The new sticker therefore stores a new grouping and placement relationship rather than baking duplicated model bytes.

If two selected nested parts use the same local instance ID, capture creates deterministic unique IDs for the new group while the exact source paths remain in the selection receipt.

Motion sample frames are rebased through the same parent transforms instead of being silently dropped.

## Nested assemblies and scaling

Nested rigid assembly transforms are composed through their parent chain.

If extraction would need to flatten through an ancestor assembly whose instance uses scale other than 1, v0.9 refuses the extraction. The current saved-assembly target contract is rigid; silently folding ancestor scale into child target frames would lose truth.

Selecting the scaled assembly itself as one child is still conceptually distinct from flattening through it; the first contract only blocks unsupported descendant flattening.

## Save and provenance

`save_selection_as_sticker` saves the result through the ordinary `axm.sticker.assembly-3d/v1` path.

The saved definition remains a normal immutable sticker. Its `origin.source` records the exact source sticker pin and the canonical selection digest. The returned receipt also records:

- source pin;
- selection digest;
- pivot path;
- each original selected path;
- its new saved instance ID;
- its exact child sticker pin and rebased target.

Portable library export still follows ordinary exact dependency closure, so source model bytes remain deduplicated by digest.

## Preserving useful connection points

Selection capture can optionally expose named ports from selected source pieces on the new sticker.

The caller explicitly names which selected source path + source port should become which new port ID. Sticker Fabric copies the existing interface, role, accepted peer roles, and computes the port's rigid frame in the extracted sticker's new local coordinates.

This preserves known connection evidence without inventing a new boundary ontology. Automatic detection of which cut connections *should* become public ports is outside v0.9 unless the caller supplies that authoring intent.

Scaled selected instances cannot contribute exposed rigid ports in v0.9.

## Human / machine parity

The same JSON surface is available to a local editor, script, AI, or machine caller:

- `selection_manifest` — list exact addressable instance paths for an exact saved assembly;
- `extract_selection` — preview the rebased copy without mutating the Registry;
- `save_selection_as_sticker` — save the exact selection as an ordinary v1 assembly sticker.

A graphical editor can therefore implement ordinary copy/select/save UX while still submitting the same explicit evidence contract used by machine callers.

## What v0.9 proves

It proves that a reusable sticker can be captured from a larger deterministic design without duplicating source assets, losing exact child identity, or requiring a new sticker schema.

The Microforge regression selects `beam-x`, `column`, and `cap` from inside `corner-0` of the nested `microforge-demo`, rebases them around the beam, saves them as a new module, exports exact portable closure, and preserves explicitly chosen beam/column named ports.

## What it does not prove

Selection capture does **not** prove:

- that an arbitrary screenshot region maps to one structural selection;
- mesh-level segmentation or Boolean cutting;
- geometric connectivity or non-intersection;
- that every visually nearby item belongs in the same reusable module;
- automatic semantic naming;
- automatic inference of which boundary ports should be public;
- physical validity, strength, collision clearance, aesthetics, or target-engine quality.

Those can be separate evidence-backed layers later. The first rule is simple: when the structure is known, copy the known structure exactly.
