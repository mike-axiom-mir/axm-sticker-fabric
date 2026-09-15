import math
import unittest

from axm_stickers import resolve_family, validate_family, value_map


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
    def test_named_variant_derives_exact_relationships(self):
        result = resolve_family(wheel_family(), variant="compact")
        values = value_map(result)
        self.assertAlmostEqual(values["circumference"], math.tau * 0.35)
        self.assertAlmostEqual(values["hub_ratio"], 0.1 / 0.35)
        self.assertEqual(result["parameters"]["radius"]["selected_by"], "variant")
        self.assertTrue(result["constraints"][0]["passed"])

    def test_explicit_override_has_priority_and_keeps_evidence(self):
        result = resolve_family(wheel_family(), variant="compact", overrides={"radius": 0.4})
        self.assertEqual(result["parameters"]["radius"]["value"], 0.4)
        self.assertEqual(result["parameters"]["radius"]["selected_by"], "override")
        self.assertEqual(result["parameters"]["radius"]["truth"], "measured")
        self.assertEqual(result["parameters"]["radius"]["uncertainty"], 0.002)

    def test_range_and_constraints_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "exceeds declared range"):
            resolve_family(wheel_family(), overrides={"radius": 2.0})
        with self.assertRaisesRegex(ValueError, "math constraints failed"):
            resolve_family(wheel_family(), overrides={"radius": 0.3, "hub_radius": 0.2})

    def test_expression_language_does_not_execute_arbitrary_code(self):
        family = wheel_family()
        family["derived"]["circumference"]["expr"] = {"python": "__import__('os').system('echo nope')"}
        with self.assertRaises(ValueError):
            validate_family(family)

    def test_truth_boundary_does_not_claim_physics(self):
        result = resolve_family(wheel_family())
        self.assertIn("dimensional consistency", result["truth_boundary"])
        self.assertIn("physical realism", result["truth_boundary"])


if __name__ == "__main__":
    unittest.main()
