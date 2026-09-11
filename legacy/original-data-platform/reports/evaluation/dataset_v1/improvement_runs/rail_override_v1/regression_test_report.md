# Rail override v1 regression report

Candidate branch: improve/rail-override-v1

## Verification

- Full test suite: 225 passed
- Production import smoke: PASS
- Candidate summary parsing: PASS
- Frozen dataset journeys: 700 / 700
- Candidate run failures: 0
- Ground Truth used during inference: NO
- GPS label leakage: NONE
- Existing model, feature engineering, window size, emission, reward, and UI logic: unchanged

## Existing regression coverage

The full suite includes the existing integration, Transit Context, mock UI, emission, distance, and resolver tests. The new rail guard also has a dedicated resolver regression test.

No main merge or release tag is created in this branch. Release remains gated on this report and final Git audit.
