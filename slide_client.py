import socket, pyautogui
from config import PORT, LOG_DIR
import pathlib, datetime

pyautogui.PAUSE=0.05; pyautogui.FAILSAFE=True

# ----- 로깅 -----
LOG_DIR=pathlib.Path(LOG_DIR); LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"B_slide_{datetime.date.today():%Y%m%d}.csv"
def log(txt):
    ts=datetime.datetime.now().isoformat(timespec="milliseconds")
    log_file.open("a",encoding="utf-8").write(f"{ts},{txt}\n")

def show_start(): pyautogui.press("f5"); log("SHOW_START")
def show_end():   pyautogui.press("esc"); log("SHOW_END")
def next_slide(): pyautogui.press("right"); log("NEXT")
def prev_slide(): pyautogui.press("left");  log("PREV")

sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind(("0.0.0.0",PORT))
print(f"[B] listening {PORT}")

cmd_map={"SHOW_START":show_start,"SHOW_END":show_end,
         "NEXT":next_slide,"PREV":prev_slide}

while True:
    data,addr=sock.recvfrom(1024); cmd=data.decode().strip()
    if cmd=="END": break
    func=cmd_map.get(cmd); 
    if func: func(); print(">>",cmd)