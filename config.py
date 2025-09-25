# ----------------- 네트워크 설정 -----------------
A_IP = "192.168.1.100"   # EEG PC  (telescan)
B_IP = "192.168.1.103"   # 슬라이드 PC (power-point)
PORT = 4210              # 단일 포트

# EEG 데이터 수신 설정
EEG_UDP_IP = "192.168.1.105"    # EEG 데이터 수신 IP (C 컴퓨터)
EEG_UDP_PORT = 5000             # EEG 데이터 수신 포트

# ----------------- 파일/기타 ---------------------
SCENARIO_FILE = "scenario.yaml"
LOG_DIR = "logs"      # 각종 로그 저장 폴더
EEG_DATA_DIR = "eeg_data"  # EEG 데이터 저장 폴더