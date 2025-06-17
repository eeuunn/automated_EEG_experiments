import socket, pyautogui, time, pathlib, datetime
from config import PORT, LOG_DIR
pyautogui.PAUSE=0.05; pyautogui.FAILSAFE=True

# ----- 로깅 -----
LOG_DIR=pathlib.Path(LOG_DIR); LOG_DIR.mkdir(exist_ok=True)
log_file = LOG_DIR / f"A_eeg_{datetime.date.today():%Y%m%d}.csv"
def log(txt):
    ts=datetime.datetime.now().isoformat(timespec="milliseconds")
    log_file.open("a",encoding="utf-8").write(f"{ts},{txt}\n")

# ----- Telescan 핫키 (연구실에 맞게 수정) -----
def telescan_start(): pyautogui.hotkey("ctrl","n")
def record_on():      pyautogui.press("f5"); log("REC_START")
def record_off():
    pyautogui.press("f6")
    fname=f"EEG_{datetime.datetime.now():%H%M%S}"
    time.sleep(0.2); pyautogui.typewrite(fname); pyautogui.press("enter")
    log(f"REC_SAVED:{fname}")
def mark_resp():      pyautogui.press("f9"); pyautogui.typewrite("RESP"); pyautogui.press("enter")

# ----- UDP 수신 -----
sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
sock.bind(("0.0.0.0",PORT))
print(f"[A] listening {PORT}")

cmd_map={"REC_ON":record_on,"REC_OFF":record_off,"MARK_RESP":mark_resp}

while True:
    data,addr=sock.recvfrom(1024); cmd=data.decode().strip()
    if cmd=="END": break
    func=cmd_map.get(cmd); 
    if func: func(); print(">>",cmd)