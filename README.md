# IMU GPS Logger - 104Hz Data Recording System

## 시스템 요구사항
- Python 3.8 이상
- Windows OS (COM 포트 사용)
- STM32F401RE 보드 (USB 연결)

## 설치 방법

### 1. 필요 패키지 설치
```bash
pip install pyserial psutil
```

### 2. STM32 보드 연결
- STM32F401RE를 USB로 연결
- 장치 관리자에서 COM 포트 확인 (일반적으로 COM3)

## 실행 방법

### 방법 1: 자동 모드 (권장)
포트를 자동으로 감지하고 즉시 기록을 시작합니다:
```bash
python main.py --auto
```

### 방법 2: 시간 제한 자동 모드
10초간만 기록하고 자동 종료:
```bash
python main.py --auto --duration 10
```

### 방법 3: 수동 포트 지정
특정 포트를 지정하여 실행:
```bash
python main.py --port COM3
```

### 방법 4: 도움말 보기
```bash
python main.py -h
```

## 프로그램 종료
- `Ctrl + C`를 누르면 안전하게 종료됩니다
- 데이터가 자동으로 CSV 파일로 저장됩니다

## 출력 파일
`logs/` 폴더에 다음 파일들이 생성됩니다:
- `YYYYMMDD_HHMMSS_raw_imu_gps_data.csv` - 104Hz IMU 원시 데이터
- `YYYYMMDD_HHMMSS_eskf_imu_gps_data.csv` - ESKF 필터링 데이터

## 실시간 모니터링
프로그램 실행 중 다음 정보가 실시간으로 표시됩니다:
- 현재 데이터 수집률 (Hz)
- 평균 데이터 수집률
- 총 수집 샘플 수
- 메모리 사용량
- 버퍼 상태

## 성능 목표
- 목표 수집률: 104 Hz (IMU)
- GPS 업데이트: 1 Hz
- 데이터 유효성: > 99%
- 데이터 손실: 0

## 데이터 형식
### IMU 데이터
```
IMU: Acc[x,y,z] Gyro[x,y,z]
```

### GPS 데이터
```
GPS: Lat[위도] Lng[경도] Status[VALID/SEARCHING]
```

### 통합 데이터
```
DATA: IMU[ax,ay,az,gx,gy,gz] GPS[lat,lng,status]
```

## 테스트 실행
각 모듈을 개별적으로 테스트할 수 있습니다:

```bash
# 포트 스캔 테스트
python test/test_port_scan.py

# 연결 테스트
python test/test_connection.py

# 배치 읽기 성능 테스트
python test/test_batch_read.py

# CSV 기록 테스트
python test/test_csv_logger.py

# 데이터 검증 테스트
python test/test_data_validator.py

# 성능 모니터 테스트
python test/test_performance_monitor.py
```

## 문제 해결

### 포트를 찾을 수 없음
1. STM32가 USB로 연결되어 있는지 확인
2. 장치 관리자에서 COM 포트 확인
3. STM32 드라이버가 설치되어 있는지 확인

### 데이터 수집률이 낮음
1. USB 케이블이 정상인지 확인
2. 다른 프로그램이 COM 포트를 사용하는지 확인
3. PC 성능이 충분한지 확인

### CSV 파일이 생성되지 않음
1. `logs/` 폴더 권한 확인
2. 디스크 공간 확인
3. 프로그램을 정상 종료했는지 확인 (Ctrl+C)