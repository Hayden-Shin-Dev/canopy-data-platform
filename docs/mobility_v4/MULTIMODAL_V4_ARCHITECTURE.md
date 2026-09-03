# Mobility V4 architecture

V4 is isolated from the V3 production selector and artifacts. The current
code contains only the official contract guardrail in
`src/mobility_v4/contracts.py` and a non-destructive runtime check in
`scripts/run_aihub_official_smoke.py`.

The official pipeline is:

1. raw GPS, IMU, AP and BTS files
2. official preprocessing (one 60-second section)
3. `(340, 60)` tensor
4. official DenseNet checkpoint
5. 11-class logits

The downloaded Validation tree currently contains GPS and labels only. It is
not passed through a fabricated full-modality tensor. Once the missing raw
sensor trees are available, ablations (full, GPS+IMU, GPS-only) will be run on
Validation only, with Test reserved for the final selection.
