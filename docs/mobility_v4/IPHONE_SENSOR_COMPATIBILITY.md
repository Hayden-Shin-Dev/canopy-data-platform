# iPhone sensor compatibility

The official AI-Hub checkpoint requires GPS, IMU, Wi-Fi/AP and BTS/cell
features. CoreLocation can provide GPS and CoreMotion can provide motion
signals, but public iOS APIs do not provide the BSSID stream or cellular
`ci`/`pci` history used by the official preprocessor.

The official preprocessing also rejects IMU sessions whose samples are not
exactly 100 Hz. We therefore do not zero-fill AP/BTS or claim that a phone
can produce the official `(340, 60)` tensor. A production V4 adapter needs a
newly trained GPS+IMU or GPS-only model, evaluated on validation data first.

Current evidence is in `reports/mobility_v4/OFFICIAL_MODEL_SMOKE.json`.
