from __future__ import annotations

import unittest

from src.geolife.mode_mapping import CANOPY_MODES, canonicalize_mode


class GeoLifeModeMappingTests(unittest.TestCase):
    def test_expected_raw_modes_map_to_canopy_modes(self) -> None:
        expected = {
            "walk": "walk",
            "bike": "bike",
            "car": "car",
            "bus": "bus",
            "taxi": "car",
            "subway": "rail",
            "train": "rail",
        }
        for raw_mode, canonical_mode in expected.items():
            self.assertEqual(canonicalize_mode(raw_mode), canonical_mode)
        self.assertTrue(set(expected.values()).issubset(CANOPY_MODES))

    def test_excluded_modes_return_none(self) -> None:
        for raw_mode in ("airplane", "boat", "motorcycle", "run"):
            self.assertIsNone(canonicalize_mode(raw_mode))

    def test_whitespace_and_case_are_normalized(self) -> None:
        self.assertEqual(canonicalize_mode("  TRAIN "), "rail")

    def test_unknown_mode_is_not_silently_mapped(self) -> None:
        with self.assertRaises(ValueError):
            canonicalize_mode("unknown")


if __name__ == "__main__":
    unittest.main()
