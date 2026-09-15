# Microforge evidence wave

Microforge is the first deliberately small-part growth set for the Sticker Fabric.
Its purpose is not to claim a finished art library. It exercises whether exact,
editable, reusable pieces can be composed repeatedly into larger saved assets
without changing the sticker schema or introducing UC as a registry dependency.

## What is generated

`python tools/build_microforge_library.py OUTPUT.json` deterministically creates
an `axm.sticker-library/v1` bundle containing:

- 12 original rigid GLB micro-parts: cube, plate, beam, column, brace, pin, axle,
  hub, wheel, disc, cap and marker;
- one exact editable `axm.procedural-3d/v0.1` JSON source for every GLB;
- three saved reusable modules: corner, wheel and panel;
- one nested `microforge-demo` assembly that reuses those modules and primitives.

The 16 definitions expand to 67 placed records. Binary GLBs and editable JSON
sources are retained once by digest in the portable library, not duplicated for
every placement. `examples/microforge-summary.json` pins the expected root digest,
counts and IDs without storing a second large base64 copy of the generated bundle.

The generator uses only the Python standard library and is an authoring tool,
not a registry runtime dependency. Geometry values derived from trigonometry or
normalization are quantized to 12 decimal places before canonical serialization;
this prevents host math-library noise from silently changing exact GLB hashes.
The registry still does not render, generate, or execute creative recipes.

## Evidence checked in CI

`tests/test_microforge_library.py` regenerates the library twice and requires
byte-identical JSON output. It then imports that output through the real Registry,
expands the root assembly, exercises graph search and reverse-use discovery, and
exports the exact dependency closure again.

The same summary/root digest assertion runs in the repository's Python 3.11 and
3.13 jobs on both Ubuntu and Windows. A platform that emits different canonical
Microforge bytes therefore fails the evidence gate instead of being accepted as
approximately equivalent.

For every rigid part the test also verifies:

- asset SHA-256 matches its exact registry reference;
- glTF binary header and declared file length are internally consistent;
- the JSON chunk declares glTF 2.0 and one explicit scene;
- no skin or external image dependency is present;
- the retained editable source parses as `axm.procedural-3d/v0.1` and keeps the
  same authored name as the sticker definition.

These are structural and provenance checks. They are not visual-quality,
physics, collision, UV, target-engine or aesthetic acceptance evidence.

## What the current v1 contract handled well

This real composition exercise did not require a sticker schema change. Existing
v1 contracts already support:

- exact immutable part/version pins;
- nested saved assemblies;
- shared source bytes instead of per-placement duplication;
- independent placement transforms;
- portable closure/import;
- searchable semantic tags;
- direct and reverse composition evidence in Registry v2;
- original editable source retained beside a derived rigid GLB.

That is enough to build useful compound assets from many small exact pieces.

## Limits exposed by building with it

Microforge also makes several current boundaries concrete instead of theoretical:

1. **One attachment anchor per sticker.** A rigid sticker declares one socket kind
   and one source anchor. A part cannot yet expose multiple named connection sites
   such as `left-end`, `right-end`, `axle`, and `panel-face` in one definition.
2. **Uniform 3D instance scale only.** Different beam/plate proportions therefore
   remain distinct authored stickers instead of one box stretched independently
   on X/Y/Z at placement time.
3. **No declared connection-role vocabulary.** Tags can say `role-wheel` or
   `role-fastener`, but the assembly contract does not distinguish structural,
   rotational, decorative or load-bearing ports as machine-checkable interfaces.
4. **Socket compatibility is structural, not geometric.** Matching socket kinds
   and rigid frames do not prove that two meshes intersect correctly, avoid
   collision, or make visual sense.
5. **Material variation remains authored source.** The rigid adapter does not
   promise arbitrary per-instance PBR material mutation.

These are observations from an actual nested reusable library, not reasons to
silently widen the schema. A future schema revision should only adopt additional
vocabulary when more real libraries demonstrate that the same missing concept is
repeatedly useful and can be bounded without breaking source integrity.

## Candidate next experiments, not canon

The strongest evidence-backed experiments are multiple named anchors per rigid
part and explicit connection roles layered above existing socket compatibility.
A controlled non-uniform-scale experiment may also be useful, but it should first
measure how scaling affects anchors, normals, collision expectations and exported
GLB behavior rather than treating convenience as proof of a safe contract.
