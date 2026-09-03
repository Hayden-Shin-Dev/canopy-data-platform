# Canopy 데모 EXE

현재 프로젝트 폴더에서 `scripts/build_canopy_demo.ps1`를 한 번 실행하면 `dist/CanopyDemo.exe`가 만들어진다.

`dist/CanopyDemo.exe`를 더블클릭하면 로컬 데모 서버가 켜지고 기본 브라우저가 `http://127.0.0.1:8765`로 열린다. 이미 서버가 켜져 있으면 새 서버를 만들지 않고 기존 화면만 연다.

이 EXE는 모델과 데이터까지 복사하는 완전 독립 패키지가 아니다. 수 GB 모델과 데이터는 현재 Canopy 프로젝트 폴더의 `models`, `data`, `assets`, `scripts`를 그대로 사용한다. 따라서 EXE는 반드시 이 저장소의 `dist` 폴더 안에 둬야 하고, 실행 PC에는 현재 Python 환경과 프로젝트 의존성이 설치되어 있어야 한다.

종료할 때는 실행 중인 `CanopyDemo.exe`를 닫으면 된다. 서버만 남아 있으면 작업 관리자에서 `python.exe`의 `scripts/run_integration_ui.py` 프로세스를 종료하면 된다.
