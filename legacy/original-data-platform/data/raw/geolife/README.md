# GeoLife 원본 데이터

이 디렉터리는 `Geolife Trajectories 1.3` 원본을 처리할 때 사용하는 로컬 입력 위치입니다.

원본 ZIP과 압축 해제한 `Data/<user>/Trajectory/*.plt`, `Data/<user>/labels.txt`는 용량과 재배포 제한 때문에 Git에 커밋하지 않습니다. 원본은 그대로 보관하고, 분석·전처리는 원본을 읽어 새 결과를 생성하는 방식으로 실행합니다.

현재 확인한 입력 파일:

- `Geolife Trajectories 1.3.zip`
- trajectory 파일: 18,670개
- label 파일: 69개

분석 명령은 저장소 루트에서 실행합니다.

```powershell
python scripts/analyze_geolife_raw.py "C:\path\to\Geolife Trajectories 1.3.zip"
```

원본 파일의 이름, 내용, 인코딩은 처리 과정에서 수정하지 않습니다.
