# C_controller.py
import socket, time, datetime, pathlib, yaml, threading, pygame, sys, struct
from config import A_IP, B_IP, PORT, SCENARIO_FILE, LOG_DIR, EEG_DATA_DIR, EEG_UDP_IP, EEG_UDP_PORT

# ----------------- 전역 -----------------
_state = {"step":"대기 중", "remain":0.0, "running":False}
peer = {A_IP:False, B_IP:False}           # ★ 연결 확인용 플래그

# EEG 데이터 수신 관련 전역 변수
eeg_recording = False
eeg_data_file = None
eeg_sock = None
eeg_packets_received = 0
last_eeg_packet_time = 0

# ----------------- UDP 통신 -----------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))
def send(ip, msg):
    try:
        sock.sendto(msg.encode(), (ip, PORT))
        log(f"TX→{ip}:{msg}")
    except OSError as e:                   
        log(f"ERR:{ip}:{e}")               #   로그만 남기고
        peer[ip] = False                   #   연결 끊김 표시
def rx_loop():                             
    while True:
        data, addr = sock.recvfrom(1024)
        if data.decode()=="PONG":
            peer[addr[0]] = True

threading.Thread(target=rx_loop, daemon=True).start()

# ----------------- EEG 데이터 수신 관련 함수들 -----------------
def create_eeg_udp_server():
    """EEG 데이터 수신용 UDP 서버 생성"""
    global eeg_sock
    try:
        eeg_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 포트 재사용 허용
        eeg_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # 모든 인터페이스에서 수신하도록 설정
        eeg_sock.bind(("0.0.0.0", EEG_UDP_PORT))
        log(f"EEG UDP 서버 시작: 0.0.0.0:{EEG_UDP_PORT} (설정된 IP: {EEG_UDP_IP})")
        
        # 수신 버퍼 크기 증가
        eeg_sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        
        return True
    except socket.error as e:
        log(f"EEG UDP 서버 생성 실패: {e}")
        log(f"포트 {EEG_UDP_PORT}가 이미 사용 중이거나 권한이 없을 수 있습니다.")
        return False

def extract_scenario_name():
    """scenario.yaml에서 시나리오 이름 추출 (첫 번째 시나리오 단계 기반)"""
    try:
        with open(SCENARIO_FILE, encoding="utf-8") as f:
            steps = yaml.safe_load(f)["scenario"]
        
        # 첫 번째 실제 고정주시가 아닌 시나리오 단계 찾기
        for step in steps:
            name = step["name"]
            if "시나리오" in name:
                # "1. 시나리오" -> "시나리오"
                parts = name.split(".", 1)
                if len(parts) > 1:
                    return parts[1].strip()
                return name.strip()
        
        # 시나리오라는 단어가 없으면 첫 번째 단계의 번호 부분 제거
        first_step = steps[0]["name"] if steps else "unknown"
        parts = first_step.split(".", 1)
        if len(parts) > 1:
            return parts[1].strip()
        return first_step.strip()
        
    except Exception as e:
        log(f"시나리오 이름 추출 실패: {e}")
        return "unknown_scenario"

def convert_step_name_to_filename(step_name):
    """시나리오 단계 이름을 파일명용으로 변환
    예: "1. 선택지1" -> ("Q1", "choice_1"), "2. 시나리오" -> ("Q2", "scenario")
    반환: (시나리오번호, 단계명)
    """
    try:
        # 번호와 이름 분리
        parts = step_name.split(".", 1)
        if len(parts) != 2:
            # 점이 없는 경우 그대로 사용
            return ("Q0", step_name.strip().replace(" ", "_"))
        
        trial_num = parts[0].strip()
        step_type = parts[1].strip()
        
        # 단계 타입별 영어 변환
        type_mapping = {
            "선택지1": "choice_1",
            "선택지2": "choice_2", 
            "선택지3": "choice_3",
            "선택지4": "choice_4",
            "선택지5": "choice_5",
            "시나리오": "scenario",
            "고정주시": "fixation",
            "고정주시(시작)": "fixation_start",
            "고정주시(시나리오)": "fixation_scenario", 
            "고정주시1": "fixation_1",
            "고정주시2": "fixation_2",
            "고정주시3": "fixation_3",
            "고정주시4": "fixation_4",
            "고정주시5": "fixation_5",
            "고민시간 및 응답": "thinking_response",
            "ITI": "iti"
        }
        
        # 매핑된 이름이 있으면 사용, 없으면 원본을 영어식으로 변환
        if step_type in type_mapping:
            converted_type = type_mapping[step_type]
        else:
            # 한글을 영어로 간단 변환하거나 그대로 사용
            converted_type = step_type.replace(" ", "_").replace("(", "_").replace(")", "")
        
        # 시나리오 번호를 Q 형식으로 변환
        scenario_num = f"Q{trial_num}"
        
        return (scenario_num, converted_type)
        
    except Exception as e:
        # 변환 실패시 원본을 안전하게 변환
        safe_name = step_name.replace(" ", "_").replace(".", "_").replace("(", "_").replace(")", "")
        return ("Q0", safe_name)

def start_eeg_recording(current_step_name=None):
    """EEG 데이터 기록 시작"""
    global eeg_recording, eeg_data_file
    if eeg_recording:
        return
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 현재 단계 이름이 제공되면 해당 단계용 파일명 생성
    if current_step_name:
        scenario_num, step_type = convert_step_name_to_filename(current_step_name)
        # 파일명 형식: 이름_소속된시나리오(질문)_현재단계_타임스탬프
        filename = f"{subject_id}_{scenario_num}_{step_type}_{timestamp}.csv"
    else:
        # 기본 파일명 (전체 시나리오용)
        scenario_name = extract_scenario_name()
        safe_subject_id = "".join(c for c in subject_id if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_scenario_name = "".join(c for c in scenario_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = f"{safe_subject_id}_ALL_{safe_scenario_name}_{timestamp}.csv"
    
    # EEG 데이터는 별도 폴더에 저장
    filepath = EEG_DATA_PATH / filename
    
    try:
        eeg_data_file = open(filepath, 'w', encoding='utf-8')
        # 헤더 작성: 타임스탬프와 각 채널의 칼럼
        num_channels = 16
        header = 'timestamp,' + ','.join([f'ch{ch}' for ch in range(1, num_channels + 1)])
        eeg_data_file.write(header + '\n')
        eeg_data_file.flush()
        
        eeg_recording = True
        log(f"EEG 기록 시작: {filename} (저장 위치: {EEG_DATA_DIR})")
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

def eeg_data_receiver():
    """EEG 데이터 수신 스레드"""
    global eeg_recording, eeg_data_file, eeg_packets_received, last_eeg_packet_time
    num_channels = 16
    data_points_per_channel = 34  # 패킷당 각 채널의 데이터 포인트 수
    packet_count = 0
    last_log_time = time.time()
    
    log("EEG 데이터 수신 스레드 시작")
    
    while True:
        try:
            if eeg_sock is None:
                time.sleep(0.1)
                continue
            
            # 타임아웃 설정 (5초)
            eeg_sock.settimeout(5.0)
            data, addr = eeg_sock.recvfrom(2176)
            packet_count += 1
            eeg_packets_received = packet_count
            last_eeg_packet_time = time.time()
            
            # 주기적으로 수신 상태 로깅 (10초마다)
            current_time = time.time()
            if current_time - last_log_time > 10:
                log(f"EEG 데이터 수신 중: {packet_count}개 패킷 수신됨 (from {addr})")
                last_log_time = current_time
            
            if len(data) == 2176:
                if eeg_recording and eeg_data_file:
                    floats = struct.unpack('544f', data)
                    timestamp = time.time()
                    
                    # 각 채널의 데이터를 수집하여 평균값 계산
                    channel_values = []
                    for i in range(num_channels):
                        channel_data = floats[i*34:(i+1)*34]
                        channel_average = sum(channel_data) / data_points_per_channel
                        channel_values.append(channel_average)
                    
                    # 데이터를 문자열로 변환하여 CSV에 저장
                    data_str = ','.join(map(str, channel_values))
                    eeg_data_file.write(f"{timestamp},{data_str}\n")
                    eeg_data_file.flush()
            else:
                log(f"잘못된 EEG 데이터 크기: {len(data)}바이트 (예상: 2176바이트)")
                
        except socket.timeout:
            # 5초 동안 데이터가 없으면 타임아웃
            if packet_count == 0:
                log("EEG 데이터 수신 타임아웃 - EEG 장비 연결 확인 필요")
            continue
        except socket.error as e:
            log(f"EEG 소켓 오류: {e}")
            time.sleep(1)
        except Exception as e:
            log(f"EEG 데이터 수신 오류: {e}")
            time.sleep(0.1)

# ----------------- 로깅 함수 -----------------
LOG_PATH = pathlib.Path(LOG_DIR); LOG_PATH.mkdir(exist_ok=True)
EEG_DATA_PATH = pathlib.Path(EEG_DATA_DIR); EEG_DATA_PATH.mkdir(exist_ok=True)

def log(txt):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
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
    # A 컴퓨터가 연결된 경우에만 피험자 이름 전송
    if peer[A_IP]:
        send(A_IP, f"SUBJECT:{subject_id}")
    
    with open(SCENARIO_FILE, encoding="utf-8") as f:
        steps = yaml.safe_load(f)["scenario"]
    
    for st in steps:
        name,dur = st["name"], float(st["dur"])
        _state.update(step=name, remain=dur)
        
        # EEG 기록이 필요한 단계인지 확인 (A:REC_ON 명령이 있는지)
        has_rec_on = any("A:REC_ON" in item for item in st.get("send", []))
        if has_rec_on:
            # 현재 단계 이름으로 EEG 기록 시작
            start_eeg_recording(name)
        
        for item in st.get("send", []):
            tgt,cmd = item.split(":",1)
            target_ip = A_IP if tgt.strip()=="A" else B_IP
            
            # A:REC_ON, A:REC_OFF 명령은 이제 C에서 직접 처리하므로 건너뜀
            if tgt.strip()=="A" and (cmd.strip().startswith("REC_ON") or cmd.strip().startswith("REC_OFF")):
                continue
                
            # A 컴퓨터 연결 확인 후 전송, B 컴퓨터는 항상 전송 시도
            if tgt.strip()=="A" and peer[A_IP]:
                send(target_ip, cmd.strip())
            elif tgt.strip()=="B":
                send(target_ip, cmd.strip())
        
        t0=time.perf_counter()
        while (rem:=dur-(time.perf_counter()-t0))>0:
            _state["remain"]=rem; time.sleep(0.05)
        
        # EEG 기록 중지가 필요한 단계인지 확인 (A:REC_OFF 명령이 있는지)
        has_rec_off = any("A:REC_OFF" in item for item in st.get("send", []))
        if has_rec_off:
            stop_eeg_recording()
    
    # 연결된 컴퓨터들에만 종료 신호 전송
    if peer[A_IP]:
        send(A_IP,"END")
    if peer[B_IP]:
        send(B_IP,"END")
    _state.update(step="실험 종료", remain=0.0, running=False)

# ----------------- 한글 폰트 로더 -----------------
def get_korean_font(size=46, bold=False):
    """
    1. AppleGothic
    2. Malgun Gothic
    3. Nanum 고딕
    """
    prefs = ["AppleGothic", "Malgun Gothic",
             "NanumGothic", "NanumBarunGothic", "NanumSquare"]
    for name in prefs:
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)

# ----------------- Pygame UI (메인) -----------------
pygame.init()
screen = pygame.display.set_mode((640, 350))
pygame.display.set_caption("EEG 실험 컨트롤러")

FONT  = get_korean_font(46, bold=True)
SMALL = get_korean_font(26)

def ping_peers():
    peer[A_IP]=peer[B_IP]=False
    send(A_IP,"PING"); send(B_IP,"PING")

clock = pygame.time.Clock(); t_ping=0
btn_rect = pygame.Rect(460, 40, 140, 60)

# ----------------- 메인 루프 시작 전 피험자 이름 입력 -----------------
input_subject_id()

# EEG UDP 서버 초기화
eeg_server_status = create_eeg_udp_server()

while True:
    for e in pygame.event.get():
        if e.type==pygame.QUIT: pygame.quit(); sys.exit()
        if (e.type==pygame.MOUSEBUTTONDOWN and btn_rect.collidepoint(e.pos)) \
           or (e.type==pygame.KEYDOWN and e.key==pygame.K_SPACE):
            if not _state["running"]:
                _state["running"]=True
                threading.Thread(target=scenario_worker, daemon=True).start()

    if time.time()-t_ping>1.0:
        ping_peers(); t_ping=time.time()

    screen.fill((30,30,30))
    
    screen.blit(FONT.render(_state["step"], True,(255,255,255)), (40,40))
    screen.blit(FONT.render(f"{_state['remain']:.1f} s",True,(0,200,255)), (40,100))

    y0=170
    for idx,(ip,ok) in enumerate(peer.items()):
        txt=f"{'A(EEG)' if ip==A_IP else 'B(SLIDE)'} : {'연결됨' if ok else '대기..'}"
        color=(0,220,0) if ok else (220,0,0)
        screen.blit(SMALL.render(txt,True,color),(40,y0+idx*25))
    
    # EEG 서버 및 기록 상태
    y0 += 60
    eeg_server_txt = f"EEG 서버: {'활성' if eeg_server_status else '오류'}"
    eeg_server_color = (0,220,0) if eeg_server_status else (220,0,0)
    screen.blit(SMALL.render(eeg_server_txt, True, eeg_server_color), (40, y0))
    
    eeg_record_txt = f"EEG 기록: {'진행중' if eeg_recording else '대기'}"
    eeg_record_color = (255,165,0) if eeg_recording else (128,128,128)
    screen.blit(SMALL.render(eeg_record_txt, True, eeg_record_color), (40, y0+25))
    
    # EEG 데이터 수신 상태
    current_time = time.time()
    data_fresh = (current_time - last_eeg_packet_time) < 5 if last_eeg_packet_time > 0 else False
    eeg_data_txt = f"EEG 수신: {eeg_packets_received}개 패킷 ({'정상' if data_fresh else '중단'})"
    eeg_data_color = (0,220,0) if data_fresh else (220,0,0) if eeg_packets_received > 0 else (128,128,128)
    screen.blit(SMALL.render(eeg_data_txt, True, eeg_data_color), (40, y0+50))
    # START 버튼
    btn_color=(70,130,250) if not _state["running"] else (110,110,110)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=10)
    screen.blit(FONT.render("START",True,(255,255,255)), (btn_rect.x+15, btn_rect.y+10))

    pygame.display.flip(); clock.tick(30)