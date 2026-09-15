import copy
import math
import unittest

from axm_stickers import convert, resolve_family, unit_info, validate_family, value_map


def wheel_family():
    return {
        "schema": "axm.math-family/v1",
        "id": "wheel",
        "parameters": {
            "radius": {
                "unit": "m", "min": 0.2, "max": 1.0, "default": 0.5,
                "truth": "measured", "uncertainty": 0.002, "source": "fixture measurement",
            },
            "hub_radius": {
                "unit": "m", "min": 0.05, "max": 0.4, "default": 0.15,
                "truth": "empirical", "source": "fixture design range",
            },
        },
        "variants": {
            "compact": {"radius": 0.35, "hub_radius": 0.1},
            "large": {"radius": 0.8, "hub_radius": 0.2},
        },
        "derived": {
            "circumference": {
                "unit": "m", "truth": "exact",
                "expr": {"op": {"name": "mul", "args": [{"const": "tau"}, {"param": "radius"}]}},
            },
            "hub_ratio": {
                "unit": "ratio", "truth": "exact",
                "expr": {"op": {"name": "div", "args": [{"param": "hub_radius"}, {"param": "radius"}]}},
            },
        },
        "constraints": [
            {
                "label": "hub_within_wheel",
                "left": {"param": "hub_radius"},
                "op": "le",
                "right": {"op": {"name": "mul", "args": [{"param": "radius"}, 0.45]}},
            }
        ],
    }


class MathFamilyTests(unittest.TestCase):
    def test_named_variant_derives_exact_relationships_but_not_exact_measurement(self):
        result = resolve_family(wheel_family(), variant="compact")
        values = value_map(result)
        self.assertAlmostEqual(values["circumference"], math.tau * 0.35)
        self.assertAlmostEqual(values["hub_ratio"], 0.1 / 0.35)
        self.assertEqual(result["parameters"]["radius"]["selected_by"], "variant")
        self.assertTrue(result["constraints"][0]["passed"])
        self.assertEqual(result["derived"]["circumference"]["relation_truth"], "exact")
        self.assertEqual(result["derived"]["circumference"]["truth"], "measured")
        self.assertEqual(result["derived"]["hub_ratio"]["truth"], "empirical")

    def test_explicit_override_has_priority_and_keeps_evidence(self):
        result = resolve_family(wheel_family(), variant="compact", overrides={"radius": 0.4})
        self.assertEqual(result["parameters"]["radius"]["value"], 0.4)
        self.assertEqual(result["parameters"]["radius"]["selected_by"], "override")
        self.assertEqual(result["parameters"]["radius"]["truth"], "measured")
        self.assertEqual(result["parameters"]["radius"]["uncertainty"], 0.002)
        self.assertEqual(result["parameters"]["radius"]["base_uncertainty"], 0.002)

    def test_units_convert_and_dimensions_are_real_checks(self):
        self.assertEqual(convert(100, "cm", "m"), 1.0)
        self.assertAlmostEqual(convert(36, "km/h", "m/s"), 10.0)
        self.assertEqual(unit_info("m2")["dimension"], {"length": 2})
        with self.assertRaisesRegex(ValueError, "incompatible"):
            convert(1, "m", "s")

        family = wheel_family()
        family["parameters"]["radius"].update({"unit": "cm", "min": 20.0, "max": 100.0, "default": 50.0})
        family["variants"]["compact"]["radius"] = 35.0
        result = resolve_family(family, variant="compact")
        self.assertAlmostEqual(result["derived"]["circumference"]["value"], math.tau * 0.35)
        self.assertAlmostEqual(result["parameters"]["radius"]["base_value"], 0.35)

    def test_dimensionally_invalid_expression_fails_closed(self):
        family = wheel_family()
        family["parameters"]["duration"] = {
            "unit": "s", "min": 1.0, "max": 10.0, "default": 2.0, "truth": "exact"
        }
        family["derived"]["nonsense"] = {
            "unit": "m", "truth": "exact",
            "expr": {"op": {"name": "add", "args": [{"param": "radius"}, {"param": "duration"}]}},
        }
        with self.assertRaisesRegex(ValueError, "compatible dimensions"):
            validate_family(family)

        family = wheel_family()
        family["derived"]["circumference"]["unit"] = "s"
        with self.assertRaisesRegex(ValueError, "dimension"):
            validate_family(family)

    def test_angles_and_unit_quantities_preserve_semantic_dimension(self):
        family = {
            "schema": "axm.math-family/v1",
            "id": "angle",
            "parameters": {
                "heading": {"unit": "deg", "min": -360, "max": 360, "default": 90, "truth": "exact"}
            },
            "variants": {},
            "derived": {
                "sine": {
                    "unit": "ratio", "truth": "exact",
                    "expr": {"op": {"name": "sin", "args": [{"param": "heading"}]}},
                }
            },
            "constraints": [],
        }
        self.assertAlmostEqual(resolve_family(family)["derived"]["sine"]["value"], 1.0)
        bad = copy.deepcopy(family)
        bad["derived"]["sine"]["expr"] = {"op": {"name": "sin", "args": [1.0]}}
        with self.assertRaisesRegex(ValueError, "angle"):
            validate_family(bad)

    def test_range_constraints_and_tolerance_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "exceeds declared range"):
            resolve_family(wheel_family(), overrides={"radius": 2.0})
        with self.assertRaisesRegex(ValueError, "math constraints failed"):
            resolve_family(wheel_family(), overrides={"radius": 0.3, "hub_radius": 0.2})

        family = wheel_family()
        family["constraints"][0]["tolerance"] = 1
        with self.assertRaisesRegex(ValueError, "tolerance_unit"):
            validate_family(family)
        family["constraints"][0]["tolerance_unit"] = "mm"
        self.assertTrue(validate_family(family))

    def test_expression_language_does_not_execute_arbitrary_code(self):
        family = wheel_family()
        family["derived"]["circumference"]["expr"] = {"python": "__import__('os').system('echo nope')"}
        with self.assertRaises(ValueError):
            validate_family(family)

    def test_truth_boundary_names_remaining_limits(self):
        result = resolve_family(wheel_family())
        self.assertIn("dimensions were checked", result["truth_boundary"])
        self.assertIn("physical realism", result["truth_boundary"])
        self.assertIn("derived uncertainty is not yet propagated", result["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
