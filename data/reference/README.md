# Reference Data

`admin_dong_centroids_2021.csv`는 SGIS 2021 행정구역경계 API의 읍면동 응답에서
제공한 대표 `x`, `y`를 저장한다. 좌표는 SGIS UTM-K 계열 `EPSG:5179`이며,
처리 코드가 WGS84(`EPSG:4326`)로 변환한 뒤 Haversine 직선거리를 계산한다.

SGIS 원본 응답 cache는 `sgis/raw/2021/`에 두고 Git에는 포함하지 않는다.
