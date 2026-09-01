# Canopy five-screen Design QA

Source visual truth: `C:\Users\user\Downloads\ChatGPT Image 2026년 9월 2일 오전 12_51_37.png`

Implementation: `http://127.0.0.1:8765/`

## Capture 조건

- Source composite: 1614 × 977 px
- Source phone crops: Home 301 × 903, Plan 303 × 903, Start 303 × 903, In Progress 304 × 903, Complete 304 × 903
- Implementation CSS viewport: 393 × 852 px
- Implementation capture: 393 × 852 px, device scale factor 1
- Source normalization: 각 phone crop을 높이 852 px로 맞추고 원본 종횡비를 유지해 약 285 px 폭으로 축소
- Browser: Chrome headless. Codex in-app Browser는 현재 sandbox metadata 오류로 연결되지 않아 Product Design Browser Choice 규칙의 Chrome fallback을 사용함
- Final screenshots: `reports/integration/screenshots/canopy-five-screen/`
- Side-by-side evidence: `qa-compare-home.png`, `qa-compare-plan.png`, `qa-compare-start.png`, `qa-compare-active.png`, `qa-compare-complete.png`

## 비교 이력

### Iteration 1

- [P1] 첫 캡처에서 393px 화면이 브라우저 최소 폭 안에서 가운데 정렬되어 오른쪽 UI가 잘림.
  - 수정: 600px 이하 viewport에서는 phone canvas를 좌측 상단에 1:1로 고정함.
  - 재검증: 모든 최종 screenshot이 393 × 852이고 우측 bell, filter, share, My Page까지 잘림 없이 표시됨.
- [P1] Home, Start, Complete가 같은 mascot 파일을 반복 사용해 원본의 landscape, skyline, celebration 장면 차이가 사라짐.
  - 수정: 원본 art direction을 기준으로 `home-landscape.png`, `journey-start.png`, `journey-complete.png`를 각각 생성해 적용함.
  - 재검증: 세 화면의 subject, crop, 흰 여백, mint/green palette가 서로 다른 원본 장면과 대응함.
- [P2] Plan 하단의 추가 CTA가 navigation 위에서 일부 잘려 녹색 막대로 보임.
  - 수정: 원본에 없는 Plan CTA를 제거하고 중앙 leaf navigation으로 Start에 이동하도록 유지함.
  - 재검증: Plan comparison card 뒤에 바로 bottom navigation이 이어짐.
- [P2] Complete 진입 toast가 reward card를 잠시 가림.
  - 수정: 자동 완료 toast를 제거함. Carbon summary와 reward가 동시에 가리지 않고 보임.
  - 재검증: `complete.png`에서 summary, cumulative saving, reward가 한 화면에 노출됨.

### Iteration 2

최종 source/implementation 합성 비교에서 추가 P0/P1/P2 차이는 발견되지 않음.

## Required fidelity surfaces

- Fonts and typography: Noto Sans KR 400–800을 사용함. 원본의 굵은 제목, 작은 muted label, 수치 강조 계층과 줄바꿈을 유지함.
- Spacing and layout rhythm: 393 × 852 iPhone canvas, 16–18px content inset, 15–18px card radius, 가벼운 green-tinted shadow, 66px persistent bottom navigation을 적용함.
- Colors and visual tokens: deep green `#07855f`, dark green `#006a4d`, pale mint, blue transit, red destination palette가 원본과 대응함.
- Image quality and asset fidelity: Home landscape, Start mascot/skyline, Complete mascot/confetti는 별도 raster asset임. UI icon은 Phosphor icon font, map은 OpenStreetMap/Leaflet tile을 사용함. placeholder/CSS drawing으로 핵심 illustration을 대체하지 않음.
- Copy and content: 원본의 Home, 여정 계획, 여정 시작, 여정 진행 중, 여정 완료 구조를 유지함. 실제 값이 필요한 결과는 API 응답으로 채움.

## 기능 검증

- Home → Plan → Start → Active → Complete → My Page 전체 흐름: PASS
- Plan filter 5개 전환: PASS
- Start 버튼이 기존 `/api/start` Replay를 실행: PASS
- Active GPS polyline과 current marker 갱신: PASS
- 120초 Window 현재 mode/confidence 표시: PASS
- 이동 종료 버튼 → Pipeline result: PASS
- Complete CO2/distance/duration/mode sequence/Token 표시: PASS
- Token 1회 적립 및 My Page history 반영: PASS
- Developer Mode 진입/복귀: PASS
- Browser severe console errors: 0
- Full tests: 261 passed

## 허용한 데이터 제약

- 원본 Plan의 두 대체 경로 시간·비용은 현재 Route/Fare API가 없어 값을 만들지 않고 `Route API 필요`, `비용 미연동`으로 표시함.
- Active의 mode와 노선 문구는 reference sample의 버스 문구를 복사하지 않고 현재 Production Prediction/Transit 결과를 그대로 표시함.
- Home 누적 수치는 새 브라우저의 이력이 없으면 0으로 시작하며, 여정 완료 후 실제 local history 값으로 갱신됨.
- 비용과 칼로리는 현재 backend source가 없으므로 결과 화면에서 `미연동`으로 표시함.

## Follow-up polish

- P3: 실제 Route/Fare API가 추가되면 Plan의 대체 경로 시간, 비용, 도로 기반 polyline을 채울 수 있음.
- P3: 실제 사용자 profile API가 추가되면 로컬 Demo 이름과 저장 기록을 계정 데이터로 교체할 수 있음.

final result: passed
