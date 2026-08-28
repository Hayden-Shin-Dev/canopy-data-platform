import tempfile
import unittest
from pathlib import Path

from scripts.analyze_geolife_gps_quality import analyze_processed_quality


class GeoLifeGpsQualityTests(unittest.TestCase):
    def test_counts_processed_feature_anomalies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "windows.csv"
            path.write_text(
                "user_id,trajectory_id,valid_step_count,distance_m,displacement_m,straightness_ratio,feature\n"
                "001,t1,0,0,0,0,1\n"
                "002,t2,1,10,11,1.1,2\n"
                "003,t3,2,20,10,0.5,3\n",
                encoding="utf-8",
            )
            result = analyze_processed_quality(path)

        self.assertEqual(result["window_count"], 3)
        self.assertEqual(result["feature_anomaly_count"]["valid_step_count_zero"], 1)
        self.assertEqual(result["feature_anomaly_count"]["displacement_gt_distance"], 1)
        self.assertEqual(result["feature_anomaly_count"]["straightness_gt_1"], 1)
        self.assertEqual(result["affected_user_count"], 2)
        self.assertEqual(result["nan_count"], 0)
        self.assertEqual(result["inf_count"], 0)


if __name__ == "__main__":
    unittest.main()
