# 더 이상 사용하지 않는 파일!











"""
EEG PC (A) – Telescan 마우스 자동화 스크립트 (마커 X 버전)
- REC_ON[:label]  : 녹화 시작
- REC_OFF         : 녹화 정지·파일 저장
- END             : 실험 종료
- PING/PONG       : 연결 확인
"""

import socket, pyautogui, time, pathlib, datetime, json, yaml, re
from config import PORT, LOG_DIR
import pyperclip

# ── 피험자 ID (실험 전 여기만 수정) ─────────────────
subject_id = "subj001"

# ── 좌표 로드 ──────────────────────────────────────
coords = json.load(open("telescan_coords.json", encoding="utf-8"))
pos    = lambda key: coords[key]        # pos("REC_STOP") 식으로 호출

# ── 기본 설정 & 로그 ───────────────────────────────
pyautogui.PAUSE, pyautogui.FAILSAFE = 0.07, True
LOG_PATH = pathlib.Path(LOG_DIR); LOG_PATH.mkdir(exist_ok=True)

def log(msg: str) -> None:
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    with open(LOG_PATH / f"A_eeg_{ts[:10]}.csv", "a", encoding="utf-8") as f:
        f.write(f"{ts},{msg}\n")

# ── 전역 상태 변수 ─────────────────────────────────
cur_label     : str | None = None       # 현재 REC_ON 라벨
current_step_idx            = 0         # 시나리오 인덱스
trial                        = 1         # 회차(1, 2, …)
first_trial                  = True      # 첫 저장 여부

# ── 시나리오 로드 ──────────────────────────────────
def load_scenario(yaml_path: str = "scenario.yaml") -> list[dict]:
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)["scenario"]

scenario: list[dict] = load_scenario()

# ── 유틸리티 함수 ───────────────────────────────────
def safe_filename(s: str) -> str:
    """파일명 불가 문자를 ‘_’로 변환"""
    return re.sub(r'[\\/:*?"<>|]', "_", s)

def extract_trial_and_keyword(label: str) -> tuple[int, str]:
    """
    '1. 선택지1' → (1, '선택지1')
    숫자 없이 들어오면 trial=1 로 가정
    """
    m = re.match(r"\s*(\d+)\.\s*(.*)", label)
    return (int(m.group(1)), m.group(2).strip()) if m else (1, label.strip())

def find_step_idx_by_label(label: str) -> int:
    """label과 가장 잘 맞는 시나리오 인덱스 반환(없으면 0)"""
    t_lbl, k_lbl = extract_trial_and_keyword(label)
    for i, step in enumerate(scenario):
        t_stp, k_stp = extract_trial_and_keyword(step["name"])
        if t_lbl == t_stp and k_lbl == k_stp:
            return i
    # 키워드만 일치해도 허용
    for i, step in enumerate(scenario):
        _, k_stp = extract_trial_and_keyword(step["name"])
        if k_lbl == k_stp:
            return i
    return 0

def type_korean(text: str) -> None:
    """Telescan 파일명 입력 대화상자에 한글 붙여넣기"""
    pyperclip.copy(text)
    pyautogui.hotkey("ctrl", "v")

# ── Telescan 제어 함수 ──────────────────────────────
def record_on(label: str = "noLabel") -> None:
    """
    1) 녹화 버튼 클릭
    2) 라벨 / 시나리오 위치 업데이트
    3) 로그 기록
    """
    global cur_label, current_step_idx, trial

    cur_label       = label
    trial, _        = extract_trial_and_keyword(label)  # trial 동기화
    current_step_idx = find_step_idx_by_label(label)

    pyautogui.click(*pos("REC_START"))
    log(f"REC_START:{label}")

def record_off() -> None:
    """
    1) 녹화 중지 버튼 클릭
    2) 파일명 생성 → 저장
    3) trial +1, 로그 기록
    """
    global cur_label, current_step_idx, subject_id, trial, first_trial

    pyautogui.click(*pos("REC_STOP"))
    time.sleep(0.4)

    # ── ① 저장할 스텝 이름 결정 (직전 스텝 기준, 한글 스텝명)
    prev_idx   = max(current_step_idx - 1, 0)
    step_raw   = scenario[prev_idx]["name"]
    _, step_nm = extract_trial_and_keyword(step_raw)

    # ── ② 안전한 파일명 조립
    safe_id   = safe_filename(subject_id)
    safe_step = safe_filename(step_nm)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    fname     = f"{safe_id}_{trial:02d}회차_{safe_step}_{timestamp}.eeg"

    # ── ③ Telescan 저장 대화상자 조작
    if first_trial:
        # (1) 첫 저장 : 폴더 → 새 폴더 → 더블클릭
        type_korean(fname)
        pyautogui.press("enter"); time.sleep(0.2)
        pyautogui.press("enter")
        pyautogui.click(*pos("ARROW_DOWN"))
        pyautogui.click(*pos("DESKTOP_BTN"))
        pyautogui.click(*pos("NEW_FOLDER_BTN"))
        type_korean(safe_id); pyautogui.press("enter"); time.sleep(0.2)
        pyautogui.press("enter")                      # 폴더 열기
        pyautogui.doubleClick(*pos("FOLDER_DOUBLECLICK"))
        type_korean(fname); pyautogui.press("enter")
        pyautogui.press("enter")
        first_trial = False
    else:
        # (2) 두 번째부터는 파일명만 입력
        type_korean(fname)
        pyautogui.press("enter")
        pyautogui.press("enter")

    log(f"REC_SAVED:{fname}")
    cur_label = None
    trial    += 1          # 다음 회차 준비

# ── UDP 수신 루프 ──────────────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", PORT))
print(f"[A] mouse-control – 포트 {PORT}")

def handle_udp_message(msg: str, addr) -> None:
    """수신 문자열 파싱 → 명령 실행"""
    global subject_id

    if msg == "PING":
        sock.sendto(b"PONG", addr)
        return

    if msg.startswith("SUBJECT:"):
        subject_id = msg.split(":", 1)[1].strip()
        print(f"[A] 피험자 ID 갱신 → {subject_id}")
        return

    cmd, *arg = msg.split(":", 1)
    if   cmd == "REC_ON":   record_on(arg[0] if arg else "noLabel")
    elif cmd == "REC_OFF":  record_off()
    elif cmd == "END":      raise SystemExit

# ── (선택) 예상 파일명 미리보기 ────────────────────
def preview_filenames(topic: str = "주제A") -> None:
    """시나리오 돌면서 A:REC_OFF 마다 예상 파일명 출력"""
    t = 1
    for i, st in enumerate(scenario):
        if any(s.startswith("A:REC_OFF") for s in st.get("send", [])):
            prev = scenario[i-1]["name"]
            _, step_nm = extract_trial_and_keyword(prev)
            print(f"{subject_id}_{topic}_{t:02d}회차_{safe_filename(step_nm)}.eeg")
            t += 1

# preview_filenames()    # ← 필요하면 주석 해제

# ── Main Loop ────────────────────────────────────
try:
    while True:
        raw, addr = sock.recvfrom(1024)
        handle_udp_message(raw.decode().strip(), addr)

except SystemExit:
    print("[A] 실험 종료 신호 수신 → 스크립트 종료")
finally:
    sock.close()