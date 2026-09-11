# Improvement priorities

이 파일은 진단 결과에 따른 제안만 담으며 Production 코드를 변경하지 않습니다.

## P0

- walk/bike/car를 rail로 바꾸는 false transit activation을 trace 단위로 재현하고 resolver 입력을 점검합니다.

## P1

- bus evidence coverage와 Raw bus recall을 먼저 보강합니다.
- car/bus/rail 분리를 위한 독립 실험을 별도 branch에서 수행합니다.

## P2

- transition timing과 segmentation 개선을 ablation으로 검증합니다.
