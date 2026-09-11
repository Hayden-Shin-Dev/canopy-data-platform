# GeoLife 원본 확인 결과

분석 대상은 `Geolife Trajectories 1.3.zip`입니다. ZIP 내부의 원본 파일만 읽었으며, 원본 파일을 추출하거나 수정하지 않았습니다.

## 파일 구조

- ZIP member: 19,106개
- `Data/<user>/Trajectory/*.plt`: 18,670개
- trajectory 사용자: 182명 (`000`~`181`)
- `Data/<user>/labels.txt`: 69개 사용자
- 별도 문서: `User Guide-1.3.pdf`

## 원본 규모와 기본 품질

- trajectory GPS point: 24,876,978개
- trajectory의 malformed row: 0개
- 모든 trajectory 파일이 비어 있지 않음
- label row: 14,718개
- label의 malformed row: 0개
- label 기간: 2007-04-09 10:27:08 ~ 2012-02-21 01:55:47

첫 5개 trajectory를 구조 검증용으로 파싱했을 때 좌표와 timestamp 형식이 모두 정상이며, 유효하지 않은 좌표와 역순 timestamp는 발견되지 않았습니다. 이 샘플 검증 결과를 전체 데이터의 품질 보증으로 확대 해석하지 않고, 이후 parser 단계에서 동일한 검사를 다시 적용합니다.

## labels.txt의 원본 Transportation Mode

`labels.txt`에 기록된 값은 다음과 같습니다.

`walk` 6,460, `bus` 2,853, `bike` 2,089, `taxi` 1,179, `subway` 813, `car` 993, `train` 299, `airplane` 17, `boat` 7, `run` 6, `motorcycle` 2

이 단계에서는 원본 mode를 Canopy mode로 매핑하지 않았습니다. 매핑 규칙은 원본 문서와 실제 label 의미를 확인한 뒤 별도 설정 파일과 테스트로 관리합니다.

## 재현 명령

```powershell
python scripts/analyze_geolife_raw.py "C:\path\to\Geolife Trajectories 1.3.zip"
```
