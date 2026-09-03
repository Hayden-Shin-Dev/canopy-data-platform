# AI-Hub 공식 교통수단 판별 모델 감사

작성 기준: 2026-09-03

이 문서는 AI-Hub에서 받은 공식 모델 패키지를 현재 Canopy `main`의
Mobility V3와 비교한 1차 코드 감사 결과다. 원본 패키지와 Canopy Production
모델은 이 감사에서 변경하지 않았다.

## 1. 확인한 패키지

원본 위치는 `C:\Users\user\Downloads\교통수단 ai모델\AI모델\AI모델 교통수단 판별 20231207`이다.

| 역할 | 파일 또는 디렉터리 |
|---|---|
| 전처리 | `모델소스코드\gadftc-recognition-preprocessing` |
| CNN 모델 | `모델소스코드\gadftc-recognition-cnn_model` |
| 소스 원본 | `모델소스코드.Zip` |
| 체크포인트 | `학습모델파일\last.chk` |
| 환경 | `구축환경정보.Zip` |
| Docker | `도커이미지\image.tar.gz` |
| 실행 안내 | `도커이미지\AI모델 환경 설치가이드 교통수단 판별.md` |

압축 파일 목록을 확인했고 `__MACOSX`, `._*`, `.DS_Store`는 분석에서 제외했다.
체크포인트는 280,358,933 bytes이며 SHA-256은
`BDBEA02401A49408331E872D4F8EBACDC7FF1FF8A01421144CAD7769BF478C61`이다.

## 2. 실제 실행 경로

공식 Docker 안내의 실행 순서는 `docker load image.tar.gz` → 테스트 폴더를
`/ml/data/origin/3.Test`로 마운트한 컨테이너 실행 → 컨테이너 안에서 `run.sh`다.
소스 기준으로 전처리 진입점은
`gadftc-recognition-preprocessing/src/main.py::main_nia56`이고,
각 데이터 폴더에 대해 `preprocessing.load()`를 호출한다. 생성된 NPZ를
`gadftc-recognition-cnn_model/src/gadftc_data_module.py::NIA56DataModule`이
`Training_MAX`, `Validation_MAX`, `Test_MAX`에서 읽고,
`src/test_lightning.py`가 `LitDensenet.load_from_checkpoint()`로 체크포인트를
불러와 테스트한다.

## 3. 입력 modality와 필수 조건

전처리 `src/preprocessing.py`의 `CATS`는 AP, BTS, GPS, IMU, LABEL이다.
`_load()`는 다섯 파일을 한 번에 읽도록 목록을 zip하고, 하나라도 없거나 IMU
행 수가 timestamp 수×100이 아니면 해당 샘플을 버린다(`is_error_imu`).

실제로 사용하는 입력은 다음과 같다.

- GPS: 위도·경도·timestamp로 5초 단위 속도 min/max/mean/std를 계산한다.
- IMU: gyro, accel, linear_accel, magnetometer, gravity, rotation, pressure를
  읽고 통계·스펙트럼·수평/수직/jerk 파생값을 계산한다.
- AP: 1분 단위 고유 Wi‑Fi BSSID 개수(`pre_ap`).
- BTS: 5초 단위 cell ID(ci/pci) 개수와 변화량(`pre_bts`).
- LABEL: 학습용 정답이며 추론 입력 채널이 아니다.

따라서 GPS만 보내는 현재 iPhone 이벤트로는 원본 모델 입력을 만들 수 없다.
AP/BTS/IMU가 없을 때의 대체 경로도 소스에는 없다. 이는 선택적 센서가 아니라
샘플을 구성하는 필수 입력이다.

## 4. raw → tensor 변환

원천 GPS CSV의 실제 열은 `timestamp,accuracy,latitude,longitude,altitude`다.
라벨 CSV는 `timestamp,label,detail_label` 형식이다. 전처리는 다음 계약을
사용한다.

1. IMU는 timestamp마다 100개 행을 검사하고 센서별 파생 통계를 계산한다.
2. AP는 60초, BTS/GPS는 5초 단위로 집계한다.
3. `concat()`은 집계값을 각 시간축에 반복하고 결측치를 `MAX_NUM=123456`으로
   채운다.
4. 결과를 `(batch, 60, features)`로 만든 뒤 transpose하여
   `(batch, features, 60)`으로 저장한다.

모델 소스 `models/densenet.py::DenseNet`은 첫 레이어를
`Bottleneck(340, 256)`으로 고정하므로 최종 입력은 **340채널 × 60시점**이어야
한다. 현재 저장소의 `src/aihub/features.py`는 GPS에서 계산한 120초 canonical
feature table을 만들며 이 tensor 계약과 다르다.

전처리 소스에는 `accel_h` 등 일부 설정 키가 `rocessEachAxis`로 오타 난 부분도
있다(`config.ini`). 제공된 Docker/생성 데이터에서 실제 실행 여부를 별도로
재현하기 전에는 이 설정을 수정하거나 추측해 보정하지 않는다.

## 5. 모델과 체크포인트

프레임워크는 PyTorch Lightning이다. `config/config.yaml`과 체크포인트
`archive/data.pkl`에서 다음을 확인했다.

| 항목 | 값 |
|---|---|
| Python | 3.9.15 |
| PyTorch | 1.9.1 |
| Lightning | 1.7.7 |
| CUDA/cuDNN | 11.1 / 8.0.5 |
| DenseNet | 1D Conv DenseNet, growthRate 40, depth 190, reduction 0.5, bottleneck |
| 입력 | 340 × 60 |
| 출력 | 11 logits, softmax/argmax는 테스트 코드에서 적용 |
| 손실 | `PolyLoss` (`models/loss_poly.py`) |
| 체크포인트 상태 | epoch 199, global_step 77600, Lightning 1.7.7 |

체크포인트의 `model.fc.weight` 저장 tensor는 `[11, 2190]`, bias는 `[11]`이다.
따라서 5개 Canopy 클래스 모델로 바로 읽거나 label index를 임의로 줄일 수 없다.

## 6. 라벨 매핑

`src/loader.py` 주석과 `preprocessing.py::pre_label`에서 원본 상세 라벨은
다음과 같이 설명된다.

`2=걷기, 3=달리기, 4=자전거, 5=차량, 6=버스, 7=KTX/기차,
8=지하철, 9=오토바이, 10=전기자전거, 11=전동 킥보드, 12=택시`.

`pre_label`은 2~6, 8~12를 0~9로 재부호화하고 0, 1, 7은 -1로 제외한다.
즉 공식 학습 산출물은 Canopy의 WALK/BIKE/CAR/BUS/RAIL과 동일한 5개 클래스가
아니며, 달리기·차량 세부·KTX/기차·지하철·오토바이·전기자전거·킥보드·택시가
별도 인덱스로 남는다. 체크포인트는 11 logits이므로 소스 주석의 10개 재부호화
값과도 설정상 불일치가 있다. 정확한 class-name 배열은 제공된 소스/체크포인트에
저장돼 있지 않아 이 감사에서 임의로 확정하지 않는다.

## 7. Macro F1 0.785 검증

패키지의 소스, config, 환경 파일, 안내 문서 및 저장소 내 공식 패키지 사본을
검색했지만 `Macro F1 = 0.785`를 재현하는 결과 파일이나 평가 표를 찾지 못했다.
따라서 modality, 클래스 수, 사용자 중복 여부, split, window/stride, 평가 단위,
결측 처리와 metric 계산 방식은 **확인 불가**다. 이 수치는 현재 Canopy의
5-class, GPS-only, UID-disjoint 120초 결과와 비교할 수 있는 근거가 아니다.

공식 테스트 코드는 `test_lightning.py`에서 파일 단위 confusion matrix와 class별
F1을 계산하지만 사용자/세션 그룹 분할을 검사하지 않는다. `NIA56DataModule`은
이미 만들어진 Training/Validation/Test 디렉터리를 그대로 읽는다.

## 8. 현재 Windows 환경에서의 재현성

현재 개발 환경은 Windows의 Python 3.14.6이고, 공식 환경은 Linux 계열 CUDA
conda 환경(Python 3.9, PyTorch 1.9.1)이다. 공식 안내가 Docker 이미지와
`--gpus all`을 요구하므로 직접 설치해 현재 Canopy 환경을 덮어쓰는 방식은
사용하지 않는다. Docker 29.6.2는 설치돼 있지만, 12GB가 넘는 공식 image를
로드하거나 실행하는 작업은 별도 재현 단계에서 수행해야 하며 이번 감사에서는
원본 이미지를 변경·삭제하지 않았다.

## 9. Canopy 적용 판단

결론은 **현재 Production에 직접 사용 불가**다.

- GPS-only 이벤트와 120초 canonical table만 제공하는 현재 runtime과 입력이
  다르다.
- IMU/AP/BTS가 필수라서 CoreLocation GPS만으로는 340채널을 만들 수 없다.
- 입력 시간 계약은 60시점이며 Canopy Production은 120초 GPS window다.
- 출력 클래스가 11개이고 공식 class-name 배열이 확인되지 않아 Canopy 5-class
  mapping을 안전하게 만들 수 없다.
- 공식 Macro F1 0.785의 평가 조건도 확인되지 않았다.

재사용 가능한 부분은 1D DenseNet 설계 아이디어와 센서별 통계·스펙트럼
feature 구현을 별도 연구용으로 참고하는 정도다. 기존 Production predictor에
체크포인트를 연결하거나 결과를 5개 class로 보정하는 코드는 추가하지 않았다.

## 10. 다음 실험 조건

공식 모델을 후보로 비교하려면 별도 실험 환경에서 다음을 먼저 고정해야 한다.

1. 공식 Docker에서 제공된 Training/Validation/Test 입력을 원본 방식 그대로
   전처리하고, 생성 NPZ의 shape가 `(N, 341, 60)`(label 채널 포함)인지 확인한다.
2. raw 파일의 사용자/세션 ID를 기준으로 UID-disjoint split을 다시 감사한다.
3. 체크포인트의 11개 출력 인덱스와 공식 라벨 문서를 확인한 뒤 Canopy 5-class로
   평가할 사전 규칙을 문서화한다. 확인되지 않은 클래스는 합치지 않는다.
4. 동일한 독립 holdout에서 공식 모델과 Canopy V3를 각각 원본 계약으로 평가하고
   Accuracy, Macro/Weighted F1, class별 precision/recall/F1, confusion matrix를
   산출한다.
5. 위 결과가 있고 입력을 실제 iPhone에서 수집할 수 있다는 근거가 생긴 뒤에만
   별도 candidate artifact를 만들고 Production 교체 여부를 검토한다.

현재 상태에서는 Canopy V3(`models/mobility_recognition/aihub_canonical_raw120.joblib`)
와 기존 HGB/Temporal/Transit/GeoLife 경로를 그대로 유지한다.

## 원본 무결성

이번 감사에서 변경하지 않은 주요 원본 SHA-256:

- `학습모델파일\last.chk`: `BDBEA02401A49408331E872D4F8EBACDC7FF1FF8A01421144CAD7769BF478C61`
- `모델소스코드.Zip`: `F53942D264F8AD89F1EAA948C01E51014264477DE492DC4E457A61AF7DA0D631`
- `구축환경정보.Zip`: `CAC1928D007701BE0280F85F3EDD4ECBFBCB73B231A0920D0DBB07333AD42094`
- `도커이미지\image.tar.gz`: `3835700D49006397F62C1CB78F6F8FEF380A63E5260E2FACADD923406C28414E`
