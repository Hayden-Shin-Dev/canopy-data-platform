# Canopy Data Platform

Canopy 제품을 위한 통합 모노레포입니다. iPhone 애플리케이션, 백엔드/API, 머신러닝 모델, Azure 인프라, 데이터 자산, 공통 계약을 한 저장소에서 관리합니다.

## 저장소 구조

```text
apps/       배포 가능한 애플리케이션 (`ios/`, `api/`)
ml/         모델별 작업, 공통 ML 컴포넌트, ML 파이프라인
cloud/      클라우드 인프라 및 배포 정의
  azure/    Azure 전용 인프라, Functions, 파이프라인, 모니터링, 설정
data/       raw, processed, reference, fixture, cache 데이터 구조
shared/     iOS, API, ML, cloud가 함께 사용하는 계약과 설정
tools/      도메인별 개발·운영 보조 도구
tests/      컴포넌트 간 통합 테스트 및 E2E 테스트
docs/       아키텍처 및 도메인 문서
legacy/     더 이상 활성 구조에 속하지 않거나 아직 이관하지 않은 기존 구현
```

## 작업 규칙

- 팀 합의 없이 새로운 최상위 디렉터리를 만들지 않습니다.
- 실제 애플리케이션 코드는 `apps/`에 두고, 개발·운영 보조 스크립트는 `tools/`에 둡니다.
- 각 ML 예측 과제는 `ml/models/` 아래에 독립 디렉터리를 둡니다.
- ML에서만 재사용하는 코드는 `ml/shared/`, 여러 시스템이 함께 사용하는 계약은 루트의 `shared/`에 둡니다.
- Azure 전용 배포 및 인프라 정의는 `cloud/azure/`에 둡니다.
- 명시적인 합의가 없는 한 대용량 데이터셋, 모델 바이너리, 캐시, 비밀정보, 생성된 빌드 산출물은 커밋하지 않습니다.

## 기존 프로토타입

이 저장소는 원래 `Hayden-Shin-Dev/canopy-data-platform`에서 포크되었습니다. 기존 구현 중 새 구조의 소유 위치가 명확하지 않은 항목은 부분적으로 옮겨 구조를 깨뜨리지 않도록 `legacy/original-data-platform/` 아래에 원형에 가깝게 보존합니다.

`legacy/`의 코드를 활성 영역으로 옮길 때는 대상 위치가 명확하고, 같은 변경에서 import와 테스트까지 함께 정리할 수 있을 때만 진행합니다.
