# Regression test report

- Command: `pytest -q`
- Result: `230 passed, 5505 warnings`
- Production import and existing Transit/Integration tests: PASS
- Candidate A frozen evaluation: 700/700, failed 0
- Ground Truth used during inference: NO
- GPS label leakage: NO
- dataset_v1 modified: NO

Release Gate remains blocked because no candidate improved the required Bus metrics and false-bus guardrail together.

