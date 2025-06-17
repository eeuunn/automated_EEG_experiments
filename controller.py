import socket, time, datetime, pathlib, yaml, threading, pygame, sys
from config import A_IP, B_IP, PORT, SCENARIO_FILE, LOG_DIR

# ---------- UDP 전송 ----------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def send(ip, msg):
    sock.sendto(msg.encode(), (ip, PORT))
    log(f"TX→{ip}:{msg}")

# ---------- 로깅 ----------
LOG_DIR = pathlib.Path(LOG_DIR); LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"controller_{datetime.date.today():%Y%m%d}.csv"
def log(txt):
    ts = datetime.datetime.now().isoformat(timespec="milliseconds")
    log_file.open("a", encoding="utf-8").write(f"{ts},{txt}\n")

# ---------- Pygame UI ----------
pygame.init(); W,H = 600,200
screen = pygame.display.set_mode((W,H)); pygame.display.set_caption("실험 타이머")
FONT = pygame.font.SysFont("NanumGothic", 46, bold=True)
_sub = pygame.font.SysFont("NanumGothic", 30)
_now = {"step":"대기 중", "remain":0.0}

def ui():
    clock = pygame.time.Clock()
    while True:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT: pygame.quit(); sys.exit()
        screen.fill((25,25,25))
        screen.blit(FONT.render(_now["step"], True,(255,255,255)), (40,40))
        screen.blit(FONT.render(f"{_now['remain']:.1f} s", True,(0,200,255)), (40,110))
        pygame.display.flip(); clock.tick(30)
threading.Thread(target=ui, daemon=True).start()

# ---------- 시나리오 실행 ----------
def parse_send(lst):
    """['A:CMD', 'B:CMD2'] → [(IP, 'CMD'), ...]"""
    out=[]
    for item in lst:
        tgt, cmd = item.split(':',1)
        ip = A_IP if tgt.strip()=="A" else B_IP
        out.append((ip,cmd.strip()))
    return out

def run():
    steps = yaml.safe_load(open(SCENARIO_FILE, encoding="utf-8"))
    for step in steps:
        name, dur = step["name"], float(step["dur"])
        _now.update(step=name, remain=dur); log(f"BEGIN:{name}")
        for ip, cmd in parse_send(step.get("send", [])):
            send(ip, cmd)
        t0=time.perf_counter()
        while (remain:=dur-(time.perf_counter()-t0))>0:
            _now["remain"]=remain; time.sleep(0.05)
        _now["remain"]=0.0; log(f"END:{name}")
    send(A_IP,"END"); send(B_IP,"END")
    _now.update(step="실험 종료", remain=0.0)

if __name__=="__main__":
    run()