# Canopy Token Reward 흐름

User Mode의 이동 종료 화면은 Result에서 끝나지 않는다.

1. 이동 종료
2. backend가 계산한 Expected CO2, Actual CO2, Reduction 표시
3. Reduction이 양수일 때 `reduction_co2e_g / 10`을 내림해 Token 계산
4. 획득 Token count-up 애니메이션
5. localStorage에 누적된 최종 보유 Token 표시

Token 계산은 `scripts/run_integration_ui.py`의 User Mode에서만 수행한다. 이동수단, CO2 값, 감축량은 UI에서 만들지 않고 `/api/status`의 pipeline 결과를 그대로 사용한다. Ground Truth와 Developer 정보는 보상 계산에 사용하지 않는다.

## 확인 방법

```powershell
python scripts/run_integration_ui.py
```

`http://127.0.0.1:8765`에서 출근 시작 후 이동 종료를 누르면 Result 화면을 거쳐 Token Reward 화면으로 전환된다. 홈으로 돌아오면 누적 보유량을 확인할 수 있다.
