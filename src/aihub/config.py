"""AI-Hub class mapping and source constants."""

from types import MappingProxyType


CANOPY_MODES = ("walk", "bike", "car", "bus", "rail")

# Directory class names are the source label for this first ingestion pass.
AIHUB_TO_CANOPY = MappingProxyType(
    {
        "WALK": "walk",
        "BIKE": "bike",
        "CAR": "car",
        "BUS": "bus",
        "SUBWAY": "rail",
    }
)

GPS_HEADER = ("timestamp", "accuracy", "latitude", "longitude", "altitude")
LABEL_HEADER = ("timestamp", "label", "detail_label")
OD_HEADER = ("timestamp", "latitude", "longitude")
