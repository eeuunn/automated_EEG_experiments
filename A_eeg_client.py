"""
EEG PC (A) – Telescan 마우스 자동화 (마커 X)
- REC_ON[:label] : 녹화 시작
- REC_OFF        : 녹화 정지·파일 저장
- END            : 실험 종료
- PING/PONG      : 연결 확인
"""

import socket, pyautogui, time, pathlib, datetime, json
from config import PORT, LOG_DIR

# ── 실험 참가자 ID만 앞에서 바꿔 주세요 ───────────
SUBJECT_ID = "subj001"

# ── 좌표 로드 ─────────────────────────────────────
coords = json.load(open("telescan_coords.json", encoding="utf-8"))
pos = lambda key: coords[key]          # pos("REC_STOP") 식 호출

# ── 기본 설정 & 로그 ──────────────────────────────
pyautogui.PAUSE, pyautogui.FAILSAFE = 0.07, True
LOG_PATH = pathlib.Path(LOG_DIR); LOG_PATH.mkdir(exist_ok=True)
def log(msg):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    with open(LOG_PATH/f"A_eeg_{ts[:10]}.csv","a",encoding="utf-8") as f:
        f.write(f"{ts},{msg}\n")

# ── Telescan 제어 함수 ────────────────────────────
cur_label = None
def record_on(label="noLabel"):
    global cur_label
    cur_label = label
    pyautogui.click(*pos("REC_START"))
    log(f"REC_START:{label}")

def record_off():
    global cur_label
    pyautogui.click(*pos("REC_STOP"))
    time.sleep(0.4)                                # 저장 창 뜰 때까지 약간 대기

    fname = f"{cur_label}_{datetime.datetime.now():%H%M%S}"

    # 1) 파일명 입력
    pyautogui.click(*pos("FILENAME_BOX"))
    pyautogui.typewrite(fname)

    # 2) 경로 변경 → 바탕화면
    pyautogui.click(*pos("PATH_BAR"))
    pyautogui.click(*pos("DESKTOP_BTN"))
    time.sleep(0.2)

    # 3) 참가자 전용 폴더 만들기 & 진입
    pyautogui.hotkey("ctrl", "shift", "n")         # Windows 새 폴더 단축키
    pyautogui.typewrite(SUBJECT_ID); pyautogui.press("enter")
    time.sleep(0.2)
    pyautogui.doubleClick(*pos("DESKTOP_BTN"))     # 폴더가 선택된 상태면 엔터~더블클릭 둘 중 하나 사용
    time.sleep(0.2)

    # 4) Save
    pyautogui.click(*pos("SAVE_BUTTON"))
    log(f"REC_SAVED:{fname}")
    cur_label = None

# ── UDP 수신 루프 (PING 포함) ───────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"[A] mouse-control – 포트 {PORT}")

while True:
    msg, addr = sock.recvfrom(1024); msg = msg.decode().strip()
    if msg == "PING": sock.sendto(b"PONG", addr); continue
    cmd, *arg = msg.split(":", 1)

    if cmd == "REC_ON":      record_on(arg[0] if arg else "noLabel")
    elif cmd == "REC_OFF":   record_off()
    elif cmd == "END":       break