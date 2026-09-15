import math
import unittest

from axm_stickers import domain_catalog, domain_family, resolve_family


class DomainFamilyTests(unittest.TestCase):
    def test_every_builtin_family_validates_and_resolves(self):
        catalog = domain_catalog()
        self.assertGreaterEqual(len(catalog), 8)
        for entry in catalog:
            result = resolve_family(domain_family(entry["id"]))
            self.assertEqual(result["family"], entry["id"])

    def test_geometry_and_motion_relations_are_unit_aware(self):
        circle = resolve_family(domain_family("geometry.circle"), overrides={"radius": 0.5})
        self.assertAlmostEqual(circle["derived"]["area"]["value"], math.pi * 0.25)
        self.assertEqual(circle["derived"]["area"]["unit"], "m2")

        motion = resolve_family(
            domain_family("motion.linear"),
            overrides={"distance": 100.0, "duration": 10.0},
        )
        self.assertEqual(motion["derived"]["speed_mps"]["value"], 10.0)
        self.assertAlmostEqual(motion["derived"]["speed_kmh"]["value"], 36.0)

    def test_rotation_removes_angle_only_with_explicit_radian_quantity(self):
        result = resolve_family(
            domain_family("rotation.wheel"),
            overrides={"radius": 0.5, "angular_speed": math.tau},
        )
        self.assertAlmostEqual(result["derived"]["rim_speed"]["value"], math.pi)
        self.assertAlmostEqual(result["derived"]["rotation_frequency"]["value"], 1.0)

    def test_domain_library_does_not_claim_empirical_standards(self):
        for entry in domain_catalog():
            family = domain_family(entry["id"])
            for spec in family["parameters"].values():
                self.assertIn("caller-selected", spec["source"])


if __name__ == "__main__":
    unittest.main()
