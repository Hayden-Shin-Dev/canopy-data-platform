import unittest
from datetime import datetime, timedelta

from src.geolife.gps_quality import GpsQualityPolicy, GpsQualityStats, iter_quality_points
from src.geolife.raw import TrajectoryPoint


def _point(index: int, *, seconds: int, latitude: float = 37.0, altitude_ft: float = 10.0) -> TrajectoryPoint:
    return TrajectoryPoint(
        user_id="001",
        trajectory_id="trajectory",
        latitude=latitude,
        longitude=127.0,
        altitude_ft=altitude_ft,
        timestamp=datetime(2021, 1, 1) + timedelta(seconds=seconds),
    )


class GeoLifeGpsQualityPolicyTests(unittest.TestCase):
    def test_breaks_long_gap_and_extreme_speed_into_segments(self) -> None:
        points = [_point(0, seconds=0), _point(1, seconds=1, latitude=38.0), _point(2, seconds=200)]
        stats = GpsQualityStats()
        result = list(iter_quality_points(points, policy=GpsQualityPolicy(max_speed_mps=10), stats=stats))

        self.assertEqual(len(result), 3)
        self.assertEqual(result[1].trajectory_id, "trajectory#q1")
        self.assertEqual(result[2].trajectory_id, "trajectory#q2")
        self.assertEqual(stats.segment_break_speed, 1)
        self.assertEqual(stats.segment_break_long_gap, 1)

    def test_drops_duplicate_point(self) -> None:
        points = [_point(0, seconds=0), _point(1, seconds=0)]
        stats = GpsQualityStats()

        result = list(iter_quality_points(points, stats=stats))

        self.assertEqual(len(result), 1)
        self.assertEqual(stats.dropped_duplicate, 1)


if __name__ == "__main__":
    unittest.main()
