"""
슬라이드 PC (B) – PowerPoint
수신 명령:
  NEXT   다음 슬라이드
  PREV   이전 슬라이드
  END    실험 종료
  PING   연결 확인용
응답: PONG
"""
import socket, pyautogui, pathlib, datetime
from config import PORT, LOG_DIR as LOG_DIR_STR

# ----------------- 기본 설정 -----------------
pyautogui.PAUSE, pyautogui.FAILSAFE = 0.05, True
LOG_DIR = pathlib.Path(LOG_DIR_STR)
LOG_DIR.mkdir(exist_ok=True)

def log(msg):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    with open(LOG_DIR / f"B_slide_{ts[:10]}.csv", "a", encoding="utf-8") as f:
        f.write(f"{ts},{msg}\n")

def next_slide():
    pyautogui.press("right")
    log("NEXT")

def prev_slide():
    pyautogui.press("left")
    log("PREV")

# ----------------- UDP 수신 -----------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"[B] UDP 수신 대기 – 포트 {PORT}")

while True:
    data, addr = sock.recvfrom(1024)
    msg = data.decode().strip()

    if msg == "PING":
        sock.sendto(b"PONG", addr)
        continue

    if msg == "NEXT":
        next_slide()
    elif msg == "PREV":
        prev_slide()
    elif msg == "END":
        break