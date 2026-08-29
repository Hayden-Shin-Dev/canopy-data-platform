from pathlib import Path

import pandas as pd

from src.transit_context.seoul_bus_reference import read_seoul_bus_route_stops


def test_seoul_source_uses_node_id_and_keeps_route_order(tmp_path: Path) -> None:
    path = tmp_path / "seoul.xlsx"
    frame = pd.DataFrame(
        {
            "ROUTE_ID": ["r1", "r1"],
            "노선명": ["100", "100"],
            "순번": [1, 2],
            "NODE_ID": ["n1", "n2"],
            "ARS_ID": ["001", "002"],
            "정류소명": ["A", "B"],
            "X좌표": [126.9, 126.91],
            "Y좌표": [37.5, 37.51],
        }
    )
    frame.to_excel(path, index=False)
    stops, route_stops, summary = read_seoul_bus_route_stops(path)
    assert stops["stop_id"].tolist() == ["n1", "n2"]
    assert route_stops["stop_sequence"].tolist() == [1, 2]
    assert summary["join_key"] == "NODE_ID"
    assert summary["route_stop_coordinate_coverage"] == 1.0
