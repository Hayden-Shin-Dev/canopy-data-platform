from src.transit_context.settings import load_settings


def test_load_transit_settings() -> None:
    settings = load_settings()
    assert settings.coordinate_system == "WGS84 (EPSG:4326)"
    assert settings.radii_m["bus_stop"] == 150
    assert settings.weights["bus_route"] == 0.30
