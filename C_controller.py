# C_controller.py  (핵심 변경 부분에 ★표시)
import socket, time, datetime, pathlib, yaml, threading, pygame, sys
from config import A_IP, B_IP, PORT, SCENARIO_FILE, LOG_DIR

# ───── 전역 ──────────────────────────────────────────────────
_state = {"step":"대기 중", "remain":0.0, "running":False}
peer = {A_IP:False, B_IP:False}           # ★ 연결 확인용 플래그

# ───── UDP 통신  (수신 스레드 추가) ───────────────────────────
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))
def send(ip, msg):
    try:
        sock.sendto(msg.encode(), (ip, PORT))
        log(f"TX→{ip}:{msg}")
    except OSError as e:                   # ★ 추가
        log(f"ERR:{ip}:{e}")               #   로그만 남기고
        peer[ip] = False                   #   연결 끊김 표시
        # 프로그램은 계속 실행
def rx_loop():                             # ★ 항상 돌면서 PONG 수집
    while True:
        data, addr = sock.recvfrom(1024)
        if data.decode()=="PONG":
            peer[addr[0]] = True

threading.Thread(target=rx_loop, daemon=True).start()

# ───── 로깅 함수 ─────────────────────────────────────────────
LOG_PATH = pathlib.Path(LOG_DIR); LOG_PATH.mkdir(exist_ok=True)
def log(txt):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    with open(LOG_PATH / f"controller_{ts[:10]}.csv","a",encoding="utf-8") as f:
        f.write(f"{ts},{txt}\n")

# ───── 시나리오 스레드 (START 되면 실행) ──────────────────────
def scenario_worker():
    with open(SCENARIO_FILE, encoding="utf-8") as f:
        steps = yaml.safe_load(f)
    for st in steps:
        name,dur = st["name"], float(st["dur"])
        _state.update(step=name, remain=dur)
        for item in st.get("send", []):
            tgt,cmd = item.split(":",1)
            send(A_IP if tgt.strip()=="A" else B_IP, cmd.strip())
        t0=time.perf_counter()
        while (rem:=dur-(time.perf_counter()-t0))>0:
            _state["remain"]=rem; time.sleep(0.05)
    send(A_IP,"END"); send(B_IP,"END")
    _state.update(step="실험 종료", remain=0.0, running=False)

# ────────── 한글 폰트 로더 ──────────
def get_korean_font(size=46, bold=False):
    """
    1. macOS : 'AppleGothic'
    2. Windows : 'Malgun Gothic'
    3. Nanum 패밀리(시스템·사용자 설치) 검색
    4. 없다면 Pygame 기본 Sans 사용
    """
    prefs = ["AppleGothic", "Malgun Gothic",
             "NanumGothic", "NanumBarunGothic", "NanumSquare"]
    for name in prefs:
        path = pygame.font.match_font(name, bold=bold)
        if path:                             # 찾으면 바로 사용
            return pygame.font.Font(path, size)
    return pygame.font.SysFont(None, size, bold=bold)  # 마지막 대안

# ───── Pygame UI (메인) ──────────────────────────────────────
pygame.init()
screen = pygame.display.set_mode((640, 260))
pygame.display.set_caption("EEG 실험 컨트롤러")

FONT  = get_korean_font(46, bold=True)   # ← 기존 SysFont 대신
SMALL = get_korean_font(26)

def ping_peers():                          # ★ 1초마다 핑
    peer[A_IP]=peer[B_IP]=False
    send(A_IP,"PING"); send(B_IP,"PING")

clock = pygame.time.Clock(); t_ping=0
btn_rect = pygame.Rect(460, 40, 140, 60)   # ★ 'START' 버튼 영역

while True:
    for e in pygame.event.get():
        if e.type==pygame.QUIT: pygame.quit(); sys.exit()
        # ★ 버튼 클릭 또는 Space 키 → 시작
        if (e.type==pygame.MOUSEBUTTONDOWN and btn_rect.collidepoint(e.pos)) \
           or (e.type==pygame.KEYDOWN and e.key==pygame.K_SPACE):
            if not _state["running"]:
                _state["running"]=True
                threading.Thread(target=scenario_worker, daemon=True).start()

    # 주기적 PING
    if time.time()-t_ping>1.0:
        ping_peers(); t_ping=time.time()

    # ─ UI 그리기 ─
    screen.fill((30,30,30))
    # 현 단계·남은 시간
    screen.blit(FONT.render(_state["step"], True,(255,255,255)), (40,40))
    screen.blit(FONT.render(f"{_state['remain']:.1f} s",True,(0,200,255)), (40,100))
    # 피어 연결 상태
    y0=180
    for idx,(ip,ok) in enumerate(peer.items()):
        txt=f"{'A(EEG)' if ip==A_IP else 'B(SLIDE)'} : {'연결됨' if ok else '대기..'}"
        color=(0,220,0) if ok else (220,0,0)
        screen.blit(SMALL.render(txt,True,color),(40,y0+idx*25))
    # START 버튼
    btn_color=(70,130,250) if not _state["running"] else (110,110,110)
    pygame.draw.rect(screen, btn_color, btn_rect, border_radius=10)
    screen.blit(FONT.render("START",True,(255,255,255)), (btn_rect.x+15, btn_rect.y+10))

    pygame.display.flip(); clock.tick(30)