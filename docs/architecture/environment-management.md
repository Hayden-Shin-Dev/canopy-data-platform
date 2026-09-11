# 환경 설정 관리

이 모노레포에서는 하나의 루트 `.env`를 모든 컴포넌트가 공유하지 않습니다. 실행 환경과 보안 요구사항이 다르기 때문에 컴포넌트별로 설정을 분리합니다.

## 기본 원칙

- 실제 비밀값이 들어 있는 `.env`, `Local.xcconfig` 등은 Git에 커밋하지 않습니다.
- 저장소에는 필요한 키 이름과 기본값만 담은 예시 파일을 커밋합니다.
- 한 컴포넌트의 환경 변수를 다른 컴포넌트가 직접 참조하지 않도록 합니다.
- 운영 환경의 비밀정보는 Azure Key Vault, Azure App Settings, GitHub Actions Secrets 등 배포 환경의 비밀 저장소를 사용합니다.

## 컴포넌트별 위치

```text
apps/api/.env.example          API 로컬 개발용
ml/.env.example                ML 로컬 학습·평가·추론용
apps/ios/Config/
  Local.xcconfig.example       iOS 로컬 빌드 설정용
cloud/azure/.env.example       Azure CLI·배포 보조 도구용
```

개발자는 필요한 예시 파일을 복사해 로컬 설정을 만듭니다.

```bash
cp apps/api/.env.example apps/api/.env
cp ml/.env.example ml/.env
cp cloud/azure/.env.example cloud/azure/.env
```

iOS에서는 `Local.xcconfig.example`을 `Local.xcconfig`로 복사하고 Xcode 빌드 설정에서 연결합니다.

## 공통 값이 필요한 경우

API URL, 스키마 버전처럼 여러 컴포넌트가 논리적으로 공유하는 값이라도 비밀정보가 아니라면 우선 `shared/configs/` 또는 코드 생성 가능한 계약 파일로 관리합니다. 런타임별 형식이 다른 값을 억지로 하나의 `.env` 파일로 통합하지 않습니다.

## Azure 운영 환경

로컬 `.env`는 개발 편의를 위한 입력일 뿐 운영 비밀 저장소가 아닙니다. Azure에 배포할 때는 다음과 같이 분리합니다.

- 애플리케이션 설정: Azure App Settings 또는 Container App/Function App 환경 변수
- 비밀정보: Azure Key Vault
- CI/CD 비밀정보: GitHub Actions Secrets 또는 OIDC 기반 인증
- 인프라 파라미터: `cloud/azure/`의 IaC 설정 파일

가능하면 장기 수명의 `AZURE_CLIENT_SECRET`보다 GitHub Actions와 Azure 사이의 OIDC/federated identity를 우선합니다.
