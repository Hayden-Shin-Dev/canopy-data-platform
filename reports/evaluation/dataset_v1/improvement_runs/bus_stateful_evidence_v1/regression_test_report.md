# Regression test report

- Frozen dataset evaluation: **PASS**, 700/700 journeys evaluated.
- Ground-truth leakage check: **PASS**, inference did not read ground truth.
- GPS label leakage check: **PASS**.
- Stateful accumulator tests: **PASS** (`tests/test_bus_state.py`).
- Transit integration tests: **PASS**.
- Full test suite: **PASS**, 227 passed, 5505 warnings.

후보 결과가 release gate를 통과하지 못했으므로 main과 production tag는 변경하지 않았다.
