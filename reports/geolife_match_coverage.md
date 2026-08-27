# GeoLife label match coverage

전체 `Geolife Trajectories 1.3.zip`을 parser와 interval matcher로 읽은 결과입니다. 원본 ZIP은 수정하지 않았고, 좌표 범위를 벗어난 행은 보정하지 않고 제외했습니다.

## 연결 결과

- 입력 trajectory 행: 24,876,978개
- parser가 반환한 유효 point: 24,876,977개
- parser 오류: 1개
- `matched`: 5,372,735개
- `ambiguous`: 67,880개
- `unmatched`: 19,436,362개
- label이 연결된 사용자: 64명

`ambiguous`는 여러 label interval이 같은 timestamp를 포함한 경우이며, 어느 mode도 임의로 선택하지 않았습니다.

## 연결된 원본 mode

- `walk`: 1,557,446
- `bike`: 943,184
- `bus`: 1,266,014
- `car`: 509,653
- `train`: 556,391
- `subway`: 283,869
- `taxi`: 241,109
- `airplane`: 9,193
- `boat`: 3,565
- `run`: 1,975
- `motorcycle`: 336

현재 mapping 정책으로 5개 Canopy mode에 포함되는 point는 5,357,666개입니다. `airplane`, `boat`, `motorcycle`, `run` 15,069개는 target mode와 등가 근거가 없어 제외됩니다.

## 확인된 원본 오류

`Data/020/Trajectory/20110911000506.plt:6782`의 위도가 `400.166666666667`로 기록되어 유효 범위를 벗어났습니다. 원본 값을 바꾸지 않고 non-strict 분석에서 오류로 기록했습니다.

## 재현 명령

```powershell
python -m scripts.analyze_geolife_matches "C:\path\to\Geolife Trajectories 1.3.zip"
```
