# 평가·학습 데이터 역할

현재 Canopy에서 사용하는 데이터의 역할을 아래처럼 고정한다.

## GeoLife

실제 GPS 기반 이동수단 Base Model 학습 데이터다. GeoLife window 생성과
학습 스크립트는 `data/raw/geolife`와 `data/processed/mobility_recognition`만 사용한다.

## 서울 Synthetic Training Dataset

현재는 없다. 별도 생성·검증·승인 절차가 끝나기 전에는 학습에 사용하지 않는다.

## Seoul Synthetic Evaluation v3

`data/evaluation/seoul-synthetic/evaluation_dataset_v3/`에 있는 frozen blind test다.

- 학습, validation, Feature 선택, Window 선택에 사용하지 않는다.
- Ground Truth는 production inference가 끝난 뒤 평가 단계에서만 읽는다.
- 파일과 freeze manifest를 수정하거나 재생성하지 않는다.

## Legacy dataset_v1

이전 평가와 원인 분석의 증거로만 보존한다. 현재 학습, validation, production
모델 선택에는 사용하지 않는다. 새 코드에서 입력 데이터로 연결하지 않는다.
