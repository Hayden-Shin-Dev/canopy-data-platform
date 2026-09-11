# 환경 설정 관리

이 모노레포에서는 하나의 루트 `.env`를 모든 컴포넌트가 공유하지 않습니다. 실행 환경과 보안 요구사항이 다르기 때문에 컴포넌트별로 설정을 분리합니다.

## 기본 원칙

- 실제 개인용 비밀값이 들어 있는 `.env`, `.env.local`, `*.secret.env`, `Local.xcconfig`는 Git에 커밋하지 않습니다.
- 저장소에는 필요한 키 이름과 기본값을 담은 `.env.example`을 둡니다.
- 프로젝트 기간에만 유효하고 권한이 제한된 단기 credential은 예외적으로 `.env.shared`에 둘 수 있습니다.
- `.env.shared`를 사용할 경우 저장소는 private이어야 하며, 프로젝트 종료 시 해당 credential을 반드시 revoke/rotate 합니다.
- 한 컴포넌트의 환경 변수를 다른 컴포넌트가 직접 참조하지 않도록 합니다.

## 컴포넌트별 위치

```text
apps/api/.env.example          API 로컬 개발용 템플릿
apps/api/.env.shared           팀 공유 단기 설정/credential
ml/.env.example                ML 로컬 학습·평가·추론용 템플릿
ml/.env.shared                 팀 공유 단기 설정/credential
apps/ios/Config/
  Local.xcconfig.example       iOS 로컬 빌드 설정용
cloud/azure/.env.example       Azure CLI·배포 보조 도구용 템플릿
```

개인별 설정은 예시 파일을 복사해 로컬에서 사용합니다.

```bash
cp apps/api/.env.example apps/api/.env
cp ml/.env.example ml/.env
cp cloud/azure/.env.example cloud/azure/.env
```

iOS에서는 `Local.xcconfig.example`을 `Local.xcconfig`로 복사하고 Xcode 빌드 설정에서 연결합니다.

## `.env.shared` 허용 범위

`.env.shared`는 생산성 향상을 위한 단기 프로젝트용 예외입니다. 다음 조건을 만족하는 값만 허용합니다.

- 프로젝트 기간 종료 후 자동 만료되거나 즉시 revoke 가능한 credential
- 권한 범위가 프로젝트 리소스로 제한된 credential
- 개인 계정의 장기 비밀번호, 장기 API key, production/customer data 접근 credential이 아닌 값

값이 해시처럼 보이는지는 중요하지 않습니다. 해당 문자열 자체로 인증이 가능하면 credential로 취급합니다.

## 공통 값이 필요한 경우

API URL, 스키마 버전처럼 여러 컴포넌트가 논리적으로 공유하는 비밀이 아닌 값은 우선 `shared/configs/` 또는 코드 생성 가능한 계약 파일로 관리합니다. 런타임별 형식이 다른 값을 하나의 루트 `.env`로 통합하지 않습니다.

## Azure 운영 환경

로컬 `.env` 또는 `.env.shared`는 개발 편의를 위한 입력이며 장기 운영 비밀 저장소가 아닙니다. Azure에 배포할 때는 다음과 같이 분리합니다.

- 애플리케이션 설정: Azure App Settings 또는 Container App/Function App 환경 변수
- 장기 비밀정보: Azure Key Vault
- CI/CD 인증: GitHub Actions Secrets 또는 OIDC 기반 인증
- 인프라 파라미터: `cloud/azure/`의 IaC 설정 파일

가능하면 장기 수명의 `AZURE_CLIENT_SECRET`보다 GitHub Actions와 Azure 사이의 OIDC/federated identity를 우선합니다.
