# Math-first Sticker Fabric

Sticker Fabric can now carry reusable **mathematical families** beside ordinary
render/mesh/layer recipes. The purpose is to derive what is derivable before a
consumer guesses an appearance.

The contract is `axm.math-family/v1` and is resolved by
`axm_stickers.resolve_family`.

A family declares:

- bounded numeric parameters with units, truth state, optional uncertainty and source;
- named variants such as `compact`, `large`, `residential`, or `industrial`;
- derived quantities expressed through a small JSON math language;
- explicit constraints that fail closed when a selected variant is inconsistent.

Supported operations are `add`, `sub`, `mul`, `div`, `pow`, `min`, `max`, `abs`,
`sqrt`, `sin`, `cos`, and `tan`, plus constants `pi`, `tau`, and `e`. Expressions
do not execute Python, shell commands, plugins, network calls, or arbitrary code.

## Example flow

```python
import json
from axm_stickers import resolve_family, value_map

family = json.load(open("examples/wheel-math-family.json"))
result = resolve_family(family, variant="compact")
values = value_map(result)
```

A renderer, CAD adapter, game tool, UC creation request, or human-facing editor
can bind those values into its own canonical source. The math result is evidence,
not a picture and not a claim that the object is physically correct.

## Truth boundary

`v1` deliberately does **not** claim dimensional algebra, unit conversion,
material mechanics, collision/physics simulation, manufacturability, rendered
quality, or real-world safety. Units are retained as labels and truth states
remain explicit (`exact`, `measured`, `empirical`, `estimated`, `creative`).

That boundary is intentional: mathematical knowledge should replace guessing
where the relationship is actually known, without turning an incomplete model
into fake certainty.

## Continuity

This does not change `axm.sticker/v1`, existing registry rows, assemblies,
portable bundles, or pinned sticker versions. Mathematical families are an
additional portable construction primitive. Universal Creation keeps its own
compatible local implementation and does not require this repository at runtime.
