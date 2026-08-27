# GeoLife sampling interval 확인

전체 trajectory를 파일 경계별로 나누어 timestamp 차이를 계산했습니다. 좌표 오류 1개는 원본을 수정하지 않고 parser의 non-strict 동작으로 제외했습니다.

## 결과

- 유효 point: 24,876,977개
- trajectory: 18,670개
- positive step: 24,159,407개
- zero 또는 negative step: 698,900개
- 120초 초과 gap: 81,670개
- interval p50: 2초
- interval p75: 5초
- interval p90: 5초
- interval p95: 5초
- 최대 interval: 93,298초

가장 많은 interval은 2초(7,902,232개), 1초(7,541,955개), 5초(5,988,005개) 순입니다. 따라서 sampling 간격은 사용자와 trajectory마다 다르고, 긴 gap도 존재합니다. Window 길이와 gap 처리값은 이 결과를 기준으로 후보를 비교한 뒤 설정 파일로 고정해야 합니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_sampling "C:\path\to\Geolife Trajectories 1.3.zip"
```
