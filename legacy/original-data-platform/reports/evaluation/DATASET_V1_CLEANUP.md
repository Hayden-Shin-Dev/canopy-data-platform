# dataset_v1 정리 결과

이번 정리는 모델 학습 없이 데이터 역할과 의존성을 확인하는 작업이다.

## 처리 결과

- 외부 `seoul-synthetic-journey-generator/output/dataset_v1`를 참조하는 Canopy 코드: 없음
- 실험 중 잘못 생성한 서울 adaptation script: 제거
- 실험 중 생성한 adaptation CSV와 CatBoost artifact: Canopy 작업 경로에서 제거
- production model과 v3 baseline 결과: 변경하지 않음
- 과거 dataset_v1 audit·root cause·improvement report: 보존

## 현재 기준

- GeoLife: 실제 GPS 기반 Base Model 학습 데이터
- 서울 Synthetic Training Dataset: 아직 없음
- `evaluation_dataset_v3`: frozen blind test 전용
- legacy `dataset_v1`: 과거 분석 증거 전용

## 남아 있는 dataset_v1 문자열

`reports/evaluation/dataset_v1/` 아래의 report와 결과 파일, 그리고 이를 재현하기
위한 legacy evaluation helper에 남아 있다. 이 경로는 현재 production 학습이나
모델 선택에서 호출되지 않는다. 증거 보존을 위해 삭제하지 않았다.

## 확인 명령

```powershell
rg -n -i "dataset.?v1|seoul-synthetic-journey-generator|output[\\/]dataset_v1" src scripts tests
rg -n -i "dataset.?v1|seoul-synthetic-journey-generator|output[\\/]dataset_v1" reports/evaluation
python -m pytest tests/test_evaluation_dataset_v3.py
```
