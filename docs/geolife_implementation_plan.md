# GeoLife v1 진행 계획

현재 작업 브랜치는 `dev/geolife-v1`입니다. 입력은 `Geolife Trajectories 1.3.zip` 원본이며, ZIP과 추출 원본은 Git에 넣지 않습니다.

## 확인된 입력

- trajectory: 18,670개 파일, 182명, 24,876,978개 GPS point
- labels: 69개 파일, 14,718개 row
- 원본 label 값: `walk`, `bike`, `car`, `bus`, `train`, `subway`, `taxi`, `airplane`, `boat`, `motorcycle`, `run`

## 단계

1. 원본 ZIP 구조와 기본 품질 확인
2. `.plt`와 `labels.txt` 원본 parser
3. 사용자·trajectory 단위 label 연결
4. 원본 mode 보존 및 Canopy mode 정책 확정
5. 시간 간격·좌표·속도 품질 규칙
6. GPS Feature 계산
7. 고정 길이 Window Dataset 생성
8. 사용자 기준 Train/Validation/Test 분할
9. Mobility Recognition baseline 학습과 평가
10. 연속 segment와 Multi-modal Trip 검증
11. 재실행 문서와 최종 검증

## 아직 결정하지 않은 사항

`train`/`subway`/`taxi`를 Canopy의 `rail`/`car`로 합칠지, `airplane`/`boat`/`motorcycle`/`run`을 어떻게 처리할지는 원본 문서와 프로젝트 정책을 확인한 뒤 별도 설정으로 결정합니다. 이 결정 전에는 mode mapping이나 학습 데이터를 만들지 않습니다.
