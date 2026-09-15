# Registry discovery contract

The registry is an offline evidence index around immutable sticker definitions.
It does not render, execute creative recipes, call UC, contact a service, or infer
semantic relationships that are absent from a known declarative contract.

## Registry schema v2

Sticker definitions remain `axm.sticker/v1`. Registry v2 adds only derived local
indexes:

- `discovery`: attachment space plus dependency-index state per exact sticker version.
- `links`: exact source -> target version pins for known composition contracts.

Opening a v1 registry creates these derived tables, rebuilds them from the stored
immutable definitions inside one transaction, and advances SQLite `user_version`
to 2. Sticker bodies, asset bytes, digests and portable bundle formats are not
rewritten.

## Dependency evidence

The registry currently knows two contracts well enough to index without guessing:

- `axm.sticker.assembly-3d/v1`: each child instance contributes a `child` edge.
- `axm.sticker.creative-task/v1`: each explicit dependency pin contributes a
  `dependency` edge.

Every edge keeps target `id`, `version` and SHA-256 definition digest. A direct
`dependencies` lookup reports local availability as:

- `exact`: the local target version exists with the pinned digest.
- `missing`: that id/version is not present locally.
- `digest_mismatch`: the id/version exists but is not the pinned definition.

Index states are intentionally explicit:

- `indexed`: a known contract was structurally understood and indexed.
- `malformed`: a known contract could not be indexed safely.
- `not_declared`: the adapter has no dependency contract known to this registry.

`not_declared` does **not** mean dependency-free. It means the registry refuses to
invent a relationship it cannot prove.

## Discovery operations

### `search`

Existing filters remain compatible. Additional optional filters are:

- `space`: `2d` or `3d`.
- `tags`: every listed tag is required.
- `any_tags`: at least one listed tag is required.
- `depends_on`: `{ "id": ..., "version": ... }` or the same object with an exact
  `digest`.

Search remains paginated by `after` / `limit` and returns the same sticker summary
shape as before.

### `dependencies`

Input: `id`, `ver`.

Returns the exact source pin, dependency-index state, and ordered direct links.
This is a one-hop factual graph query; callers may traverse deliberately rather
than the registry silently expanding unbounded work.

### `dependents`

Input: `id`, `ver`, optional `after` / `limit`.

Returns exact sticker versions that contain a proven link to that exact target
digest. This supports questions such as “which assemblies reuse this hinge?”
without treating an id/version digest conflict as a valid reverse dependency.

### `describe`

Returns bounded registry facts for one exact sticker version: core metadata,
parameter names, asset count/bytes/names, dependency evidence and reverse-use
count. It does not claim rendered quality, aesthetics, gameplay quality, or
fitness for an unstated purpose.

### `stats`

Returns registry version, sticker id/version counts, shared asset count/bytes,
known link count, attachment-space counts, adapter counts and dependency-index
state counts.

## Machine and human parity

All discovery operations use the same JSON request surface for humans, scripts,
AI callers and local machine workflows. The registry does not auto-promote search
results, generated work, practice output, or inferred preferences into user
state. Selection and authoring remain explicit caller actions.

## Why this matters for the sticker fabric

A large asset can be built from hundreds of small reusable pieces only if those
pieces remain independently findable, pinnable and inspectable. The graph index
turns the registry from a flat list of parts into a deterministic map of reusable
composition while preserving the exact-source and no-hidden-rewrite rules of the
fabric.
