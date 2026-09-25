# Math-first Sticker Fabric

Sticker Fabric can carry reusable **mathematical families** beside ordinary
render/mesh/layer recipes. The purpose is to derive what is derivable before a
consumer guesses an appearance.

The contract is `axm.math-family/v1` and is resolved by
`axm_stickers.resolve_family`.

A family declares:

- bounded numeric parameters with units, truth state, optional uncertainty and source;
- named variants;
- derived quantities expressed through a small JSON math language;
- explicit constraints that fail closed when a selected variant is inconsistent.

## Real unit and dimension algebra

Units are no longer decorative labels. The evaluator converts compatible units
to a shared base representation, carries dimensions through expressions, and
rejects incompatible math. `100 cm` can resolve as `1 m`; `36 km/h` can resolve
as `10 m/s`; adding a length to a duration fails.

The built-in registry currently covers dimensionless values/counts/percentages,
metric length/area/volume, mass, time, angles and rotations, frequency, velocity,
acceleration, angular speed, force, pressure, energy, power and screen pixels.
`convert()` and `unit_info()` expose the same rules to callers.

Angles have a semantic dimension in this fabric even though SI treats radians as
dimensionless. That prevents accidental operations such as `sin(1 metre)` and
makes angle removal explicit when a relation needs cycles rather than radians.

Supported operations are `add`, `sub`, `mul`, `div`, `pow`, `min`, `max`, `abs`,
`sqrt`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, and `atan2`, plus constants
`pi`, `tau`, and `e`. A `quantity` node can introduce an explicit numeric value
with a unit. Expressions do not execute Python, shell commands, plugins, network
calls, or arbitrary code.

## Truth propagation

A mathematically exact relation does not upgrade weaker evidence. If radius was
measured, `circumference = tau * radius` records the **relation** as exact while
the resulting circumference remains measured. Derived values retain their
explicit dependencies and the weakest applicable truth state from relation and
inputs.

Input uncertainty is retained and converted to base units. General uncertainty
propagation through arbitrary expressions is not implemented yet and is named in
the result truth boundary rather than silently guessed.

## Built-in relation families

`axm_stickers.domain_catalog()` exposes a first relation-only library:

- `geometry.circle`
- `geometry.box`
- `motion.linear`
- `motion.constant_acceleration`
- `waves.periodic`
- `rotation.wheel`
- `mechanism.gear_pair`
- `layout.aspect`

These encode mathematical/idealized relationships. They deliberately do **not**
claim that their reference input presets are average humans, cars, roads,
buildings, industrial standards, or other empirical facts. Standardized and
observed real-world size libraries should be added separately with explicit
provenance.

## Example flow

```python
from axm_stickers import domain_family, resolve_family, value_map

family = domain_family("motion.linear")
result = resolve_family(family, overrides={"distance": 100, "duration": 10})
values = value_map(result)
assert values["speed_mps"] == 10
assert values["speed_kmh"] == 36
```

A renderer, CAD adapter, game tool, UC creation request, or human-facing editor
can bind those values into its own canonical source. The math result is evidence,
not a picture and not a claim that the object is physically correct.

## Truth boundary

Dimension compatibility and the declared equations are checked. That still does
not establish material mechanics, collision/physics simulation, environmental
conditions, manufacturability, rendered quality, ergonomics, or real-world
safety. Idealized families state their assumptions in source metadata.

## Continuity

This does not change `axm.sticker/v1`, existing registry rows, assemblies,
portable bundles, or pinned sticker versions. Mathematical families are an
additional portable construction primitive. Universal Creation keeps its own
compatible local implementation and does not require this repository at runtime.
