"""
EEG PC (A) – Telescan 마우스 자동화 (마커 X)
- REC_ON[:label] : 녹화 시작
- REC_OFF        : 녹화 정지·파일 저장
- END            : 실험 종료
- PING/PONG      : 연결 확인
"""

import socket, pyautogui, time, pathlib, datetime, json, yaml
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
subject_id = "subj001"  # 기본값, SUBJECT 메시지로 갱신됨

# 회차 관리 변수 (실험 시작 시 1로 초기화, 이후 코드에서 증가 필요)
trial = 1

# 1회차 저장 플래그 (실험 시작 시 True, 이후 False)
first_trial = True

def load_scenario(yaml_path="scenario.yaml"):
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    scenario = data["scenario"]
    return scenario

scenario = load_scenario()

# 현재 단계 인덱스 추적용
current_step_idx = 0

def record_on(label="noLabel"):
    global cur_label, current_step_idx
    cur_label = label
    pyautogui.click(*pos("REC_START"))
    log(f"REC_START:{label}")
    # label이 단계 이름이면, 현재 단계 인덱스 갱신
    for i, step in enumerate(scenario):
        if step["name"] == label:
            current_step_idx = i
            break

def record_off():
    global cur_label, current_step_idx, subject_id, trial, first_trial
    pyautogui.click(*pos("REC_STOP"))
    time.sleep(0.4)
    prev_step_name = scenario[current_step_idx]["name"] if current_step_idx < len(scenario) else "unknown"
    fname = f"{subject_id}_{prev_step_name}_{datetime.datetime.now():%H%M%S}"
    if first_trial:
        # 1회차: 폴더 생성 및 진입
        pyautogui.typewrite(fname)  # 이름 입력
        pyautogui.press("enter")    # Enter
        time.sleep(0.2)             # 잠시 대기
        pyautogui.press("enter")    # Enter
        pyautogui.click(*pos("ARROW_DOWN"))
        pyautogui.click(*pos("DESKTOP_BTN"))
        pyautogui.click(*pos("NEW_FOLDER_BTN"))
        pyautogui.typewrite(subject_id)
        pyautogui.press("enter")
        time.sleep(0.2)
        pyautogui.press("enter")
        pyautogui.doubleClick(*pos("FOLDER_DOUBLECLICK"))
        # 피험자별/주제별/회차별 이름 입력 (여기서는 fname)
        pyautogui.typewrite(fname)
        pyautogui.press("enter")
        pyautogui.press("enter")
        first_trial = False
    else:
        # 2회차 이상: 바로 이름 입력 및 저장
        pyautogui.typewrite(fname)
        pyautogui.press("enter")
        pyautogui.press("enter")
    log(f"REC_SAVED:{fname}")
    cur_label = None
    trial += 1

# ── UDP 수신 루프 (PING 포함) ───────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"[A] mouse-control – 포트 {PORT}")

# 파일명 생성 함수
def make_filename(subject_id, topic, trial, step_name):
    return f"{subject_id}_{topic}_{trial}회차_{step_name}"

# 예시: 피험자/주제/회차 정보는 코드에서 직접 입력
topic = "주제A"
trial = 1

# 시나리오 순회하며 A:REC_OFF 명령이 있는 단계에서 파일명 생성
for i, step in enumerate(scenario):
    send_cmds = step.get("send", [])
    if any(cmd.startswith("A:REC_OFF") for cmd in send_cmds):
        if i > 0:
            prev_step_name = scenario[i-1]["name"]
            fname = make_filename(subject_id, topic, trial, prev_step_name)
            print(f"저장 파일명: {fname}")

while True:
    msg, addr = sock.recvfrom(1024); msg = msg.decode().strip()
    if msg == "PING": sock.sendto(b"PONG", addr); continue
    if msg.startswith("SUBJECT:"):
        subject_id = msg.split(":", 1)[1]
        print(f"[A] 피험자 이름 갱신: {subject_id}")
        continue
    cmd, *arg = msg.split(":", 1)
    if cmd == "REC_ON":      record_on(arg[0] if arg else "noLabel")
    elif cmd == "REC_OFF":   record_off()
    elif cmd == "END":       break