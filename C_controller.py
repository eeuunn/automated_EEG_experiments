# C_controller_LSL.py
import socket
import time
import datetime
import pathlib
import yaml
import threading
import pygame
import sys
from config import A_IP, B_IP, PORT, SCENARIO_FILE, LOG_DIR, EEG_DATA_DIR
from pylsl import StreamInlet, resolve_byprop # LSL 라이브러리 임포트

# ----------------- 전역 -----------------
_state = {"step":"대기 중", "remain":0.0, "running":False}
peer = {A_IP:False, B_IP:False}

# EEG 데이터 수신 관련 전역 변수
eeg_recording = False
eeg_data_file = None
eeg_inlet = None # 기존 eeg_sock 대신 LSL Inlet 객체 사용
eeg_stream_info = None # 스트림 정보 저장용
eeg_samples_received = 0
last_eeg_sample_time = 0

# ----------------- UDP 통신 (A, B 컴퓨터 제어용) -----------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))
def send(ip, msg):
    try:
        sock.sendto(msg.encode(), (ip, PORT))
        log(f"TX→{ip}:{msg}")
    except OSError as e:                   
        log(f"ERR:{ip}:{e}")
        peer[ip] = False
def rx_loop():                             
    while True:
        data, addr = sock.recvfrom(1024)
        if data.decode()=="PONG":
            peer[addr[0]] = True

threading.Thread(target=rx_loop, daemon=True).start()

# ----------------- LSL EEG 데이터 수신 관련 함수들 -----------------
def connect_to_lsl_stream():
    """LSL 네트워크에서 EEG 스트림을 찾아 연결합니다."""
    global eeg_inlet, eeg_stream_info
    try:
        log("LSL에서 'EEG' 타입 스트림을 찾는 중...")
        streams = resolve_byprop('type', 'EEG', timeout=5)
        
        if not streams:
            log("오류: LSL에서 EEG 스트림을 찾을 수 없습니다. C++ 프로그램을 먼저 실행했는지 확인하세요.")
            return False
        
        # 찾은 스트림에 Inlet 연결
        eeg_inlet = StreamInlet(streams[0])
        eeg_stream_info = eeg_inlet.info()
        log(f"LSL 스트림에 연결됨: {eeg_stream_info.name()} @ {eeg_stream_info.hostname()}")
        log(f"채널 수: {eeg_stream_info.channel_count()}, 샘플링 레이트: {eeg_stream_info.nominal_srate()} Hz")
        return True
    except Exception as e:
        log(f"LSL 연결 오류: {e}")
        return False

def eeg_data_receiver():
    """LSL Inlet으로부터 EEG 데이터 청크를 지속적으로 수신하는 스레드"""
    global eeg_recording, eeg_data_file, eeg_samples_received, last_eeg_sample_time
    
    log("EEG 데이터 수신 스레드 시작")
    
    while True:
        if eeg_inlet is None:
            time.sleep(1)
            continue
        
        try:
            # LSL Inlet으로부터 데이터 청크와 타임스탬프를 가져옴
            samples, timestamps = eeg_inlet.pull_chunk(timeout=1.0, max_samples=1024)
            
            if timestamps:
                last_eeg_sample_time = time.time()
                eeg_samples_received += len(timestamps)

                # EEG 기록이 활성화 상태일 때만 파일에 씀
                if eeg_recording and eeg_data_file:
                    # 수신한 모든 샘플을 파일에 기록
                    for i in range(len(timestamps)):
                        # 타임스탬프와 샘플 데이터를 쉼표로 구분하여 한 줄로 만듦
                        row_data = [timestamps[i]] + samples[i]
                        line = ','.join(map(str, row_data))
                        eeg_data_file.write(line + '\n')
                    eeg_data_file.flush() # 버퍼를 비워 즉시 파일에 쓰도록 함
        except Exception as e:
            log(f"EEG 데이터 수신 오류: {e}")
            time.sleep(1)


def start_eeg_recording(current_step_name=None):
    """EEG 데이터 기록 시작"""
    global eeg_recording, eeg_data_file
    if eeg_recording:
        return
    if not eeg_stream_info:
        log("오류: LSL 스트림 정보가 없어 EEG 기록을 시작할 수 없습니다.")
        return

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    if current_step_name:
        scenario_num, step_type = convert_step_name_to_filename(current_step_name)
        filename = f"{subject_id}_{scenario_num}_{step_type}_{timestamp}.csv"
    else:
        scenario_name = extract_scenario_name()
        filename = f"{subject_id}_ALL_{scenario_name}_{timestamp}.csv"
    
    filepath = EEG_DATA_PATH / filename
    
    try:
        eeg_data_file = open(filepath, 'w', encoding='utf-8')
        # 헤더 작성: LSL 스트림 정보에서 채널 수를 가져와 동적으로 생성
        num_channels = eeg_stream_info.channel_count()
        header = 'timestamp,' + ','.join([f'ch{ch}' for ch in range(1, num_channels + 1)])
        eeg_data_file.write(header + '\n')
        eeg_data_file.flush()
        
        eeg_recording = True
        log(f"EEG 기록 시작: {filename}")
    except Exception as e:
        log(f"EEG 파일 생성 실패: {e}")

def stop_eeg_recording():
    """EEG 데이터 기록 중지"""
    global eeg_recording, eeg_data_file
    if not eeg_recording or not eeg_data_file:
        return
    
    eeg_recording = False
    eeg_data_file.close()
    eeg_data_file = None
    log("EEG 기록 중지")

def extract_scenario_name():
    """scenario.yaml에서 시나리오 이름 추출 (첫 번째 시나리오 단계 기반)"""
    try:
        with open(SCENARIO_FILE, encoding="utf-8") as f:
            steps = yaml.safe_load(f)["scenario"]
        
        for step in steps:
            name = step["name"]
            if "시나리오" in name:
                parts = name.split(".", 1)
                if len(parts) > 1: return parts[1].strip()
                return name.strip()
        
        first_step = steps[0]["name"] if steps else "unknown"
        parts = first_step.split(".", 1)
        if len(parts) > 1: return parts[1].strip()
        return first_step.strip()
        
    except Exception as e:
        log(f"시나리오 이름 추출 실패: {e}")
        return "unknown_scenario"

def convert_step_name_to_filename(step_name):
    """시나리오 단계 이름을 파일명용으로 변환"""
    try:
        parts = step_name.split(".", 1)
        if len(parts) != 2:
            return ("Q0", step_name.strip().replace(" ", "_"))
        
        trial_num, step_type = parts[0].strip(), parts[1].strip()
        
        type_mapping = {
            "선택지1": "choice_1", "선택지2": "choice_2", "선택지3": "choice_3", "선택지4": "choice_4", "선택지5": "choice_5",
            "시나리오": "scenario", "고정주시": "fixation", "고정주시(시작)": "fixation_start",
            "고정주시(시나리오)": "fixation_scenario", "고정주시1": "fixation_1", "고정주시2": "fixation_2",
            "고정주시3": "fixation_3", "고정주시4": "fixation_4", "고정주시5": "fixation_5",
            "고민시간 및 응답": "thinking_response", "ITI": "iti"
        }
        
        converted_type = type_mapping.get(step_type, step_type.replace(" ", "_").replace("(", "_").replace(")", ""))
        
        return (f"Q{trial_num}", converted_type)
        
    except Exception as e:
        safe_name = step_name.replace(" ", "_").replace(".", "_").replace("(", "_").replace(")", "")
        return ("Q0", safe_name)

# ----------------- 로깅 함수 -----------------
LOG_PATH = pathlib.Path(LOG_DIR); LOG_PATH.mkdir(exist_ok=True)
EEG_DATA_PATH = pathlib.Path(EEG_DATA_DIR); EEG_DATA_PATH.mkdir(exist_ok=True)

def log(txt):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    print(f"[{ts}] {txt}") # 콘솔에도 로그 출력
    with open(LOG_PATH / f"controller_{ts[:10]}.csv","a",encoding="utf-8") as f:
        f.write(f"{ts},{txt}\n")

# EEG 데이터 수신 스레드 시작 (log 함수 정의 후)
threading.Thread(target=eeg_data_receiver, daemon=True).start()

# ----------------- 피험자 이름 입력 (Pygame UI) -----------------
subject_id = ""
def input_subject_id():
    global subject_id
    input_box = pygame.Rect(200, 180, 200, 40)
    color_inactive = pygame.Color('lightskyblue3')
    color_active = pygame.Color('dodgerblue2')
    color = color_inactive
    active = False
    text = ''
    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if input_box.collidepoint(event.pos):
                    active = not active
                else:
                    active = False
                color = color_active if active else color_inactive
            if event.type == pygame.KEYDOWN:
                if active:
                    if event.key == pygame.K_RETURN:
                        subject_id = text.strip()
                        if subject_id: # 이름이 입력되었을 때만 종료
                            done = True
                    elif event.key == pygame.K_BACKSPACE:
                        text = text[:-1]
                    else:
                        text += event.unicode
        screen.fill((30,30,30))
        screen.blit(FONT.render("피험자 이름 입력:", True, (255,255,255)), (40, 100))
        txt_surface = FONT.render(text, True, (255,255,255))
        width = max(200, txt_surface.get_width()+10)
        input_box.w = width
        screen.blit(txt_surface, (input_box.x+5, input_box.y+5))
        pygame.draw.rect(screen, color, input_box, 2)
        pygame.display.flip()
        clock.tick(30)

# ----------------- 시나리오 스레드 -----------------
def scenario_worker():
    if peer[A_IP]:
        send(A_IP, f"SUBJECT:{subject_id}")
    
    with open(SCENARIO_FILE, encoding="utf-8") as f:
        steps = yaml.safe_load(f)["scenario"]
    
    # 전체 시나리오에 대한 기록을 한번만 하도록 수정
    start_eeg_recording()

    for st in steps:
        name, dur = st["name"], float(st["dur"])
        _state.update(step=name, remain=dur)
        
        for item in st.get("send", []):
            tgt, cmd = item.split(":", 1)
            target_ip = A_IP if tgt.strip() == "A" else B_IP
            if (tgt.strip() == "A" and peer[A_IP]) or tgt.strip() == "B":
                send(target_ip, cmd.strip())
        
        t0 = time.perf_counter()
        while (rem := dur - (time.perf_counter() - t0)) > 0:
            _state["remain"] = rem
            time.sleep(0.05)
    
    stop_eeg_recording() # 시나리오 전체 종료 후 기록 중지
    
    if peer[A_IP]: send(A_IP, "END")
    if peer[B_IP]: send(B_IP, "END")
    _state.update(step="실험 종료", remain=0.0, running=False)

# ----------------- 한글 폰트 로더 -----------------
def get_korean_font(size=46, bold=False):
    prefs = ["AppleGothic", "Malgun Gothic", "NanumGothic", "NanumBarunGothic", "NanumSquare"]
    for name in prefs:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)

# ----------------- Pygame UI (메인) -----------------
pygame.init()
screen = pygame.display.set_mode((640, 400)) # UI 높이 약간 증가
pygame.display.set_caption("EEG 실험 컨트롤러 (LSL Version)")
FONT = get_korean_font(46, bold=True)
SMALL = get_korean_font(26)

def ping_peers():
    peer[A_IP] = peer[B_IP] = False
    send(A_IP, "PING"); send(B_IP, "PING")

clock = pygame.time.Clock(); t_ping=0
btn_rect = pygame.Rect(460, 40, 140, 60)

input_subject_id()

# --- LSL 스트림 연결 시도 ---
lsl_connected = connect_to_lsl_stream()

while True:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if (e.type == pygame.MOUSEBUTTONDOWN and btn_rect.collidepoint(e.pos)) \
           or (e.type == pygame.KEYDOWN and e.key == pygame.K_SPACE):
            if not _state["running"]:
                if not lsl_connected:
                    log("LSL 스트림이 연결되지 않아 재연결 시도 중...")
                    lsl_connected = connect_to_lsl_stream()
                
                if lsl_connected:
                    _state["running"] = True
                    threading.Thread(target=scenario_worker, daemon=True).start()
                else:
                    log("실험 시작 실패: LSL 스트림을 찾을 수 없습니다.")

    if time.time() - t_ping > 1.0:
        ping_peers()
        t_ping = time.time()

    screen.fill((30, 30, 30))
    
    screen.blit(FONT.render(_state["step"], True, (255, 255, 255)), (40, 40))
    screen.blit(FONT.render(f"{_state['remain']:.1f} s", True, (0, 200, 255)), (40, 100))

    y0 = 170
    for idx, (ip, ok) in enumerate(peer.items()):
        txt = f"{'A(EEG)' if ip == A_IP else 'B(SLIDE)'} : {'연결됨' if ok else '대기..'}"
        color = (0, 220, 0) if ok else (220, 0, 0)
        screen.blit(SMALL.render(txt, True, color), (40, y0 + idx * 25))
    
    # --- UI 상태 표시 업데이트 ---
    y0 += 60
    lsl_status_txt = f"LSL 스트림: {'연결됨' if lsl_connected else '연결끊김'}"
    lsl_status_color = (0, 220, 0) if lsl_connected else (220, 0, 0)
    screen.blit(SMALL.render(lsl_status_txt, True, lsl_status_color), (40, y0))
    
    eeg_record_txt = f"EEG 기록: {'진행중' if eeg_recording else '대기'}"
    eeg_record_color = (255, 165, 0) if eeg_recording else (128, 128, 128)
    screen.blit(SMALL.render(eeg_record_txt, True, eeg_record_color), (40, y0 + 25))
    
    current_time = time.time()
    data_fresh = (current_time - last_eeg_sample_time) < 2 if last_eeg_sample_time > 0 else False
    eeg_data_txt = f"EEG 수신: {eeg_samples_received}개 샘플 ({'정상' if data_fresh else '중단'})"
    eeg_data_color = (0, 220, 0) if data_fresh else (220, 0, 0) if eeg_samples_received > 0 else (128, 128, 128)
    screen.blit(SMALL.render(eeg_data_txt, True, eeg_data_color), (40, y0 + 50))
    
    # START 버튼
    btn_color = (70, 130, 250) if not _state["running"] else (110, 110, 110)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=10)
    screen.blit(FONT.render("START", True, (255, 255, 255)), (btn_rect.x + 15, btn_rect.y + 10))

    pygame.display.flip()
    clock.tick(30)

