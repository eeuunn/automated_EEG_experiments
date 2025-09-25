# pick_coords.py ― Telescan 전용 좌표 수집기
import pyautogui, time, json, pathlib

print("5초 안에 Telescan 창으로 이동해 주세요")
time.sleep(5)

# ▶ 필요한 좌표 키 목록 (순서대로 찍습니다)
KEYS = [
    "REC_START",        # 녹화 시작 버튼
    "REC_STOP",         # 녹화 정지 버튼
    "ARROW_DOWN",       # 아래 화살표 (폴더 경로 이동용)
    "DESKTOP_BTN",      # 바탕화면 버튼
    "NEW_FOLDER_BTN",   # 새폴더 버튼
    "FOLDER_NAME_BOX",  # 새폴더 이름 입력 칸 (필요시)
    # (여기서 키보드로 이름 입력 및 Enter)
    # (잠시 대기 후 Enter)
    "FOLDER_DOUBLECLICK", # 이름 변경창(더블클릭)
    # (여기서 피험자별/주제별/회차별 이름 입력 및 Enter, Enter)
    # --- 2회차부터는 아래만 사용 ---
    # "REC_START",      # 녹화 시작 버튼 (이미 위에 있음)
    # "REC_STOP",       # 녹화 정지 버튼 (이미 위에 있음)
    "FILENAME_BOX"      # 파일명 입력 칸 (2회차부터 바로 이름 입력)
    # (여기서 이름 입력 및 Enter, Enter)
]

coords = {}
for key in KEYS:
    print(f"\n{key} 위치로 마우스를 옮긴 뒤 3초만 기다려 주세요")
    time.sleep(3)
    x, y = pyautogui.position()
    coords[key] = (x, y)
    print(f"{key} 기록 완료: {x}, {y}")

path = pathlib.Path("telescan_coords.json")
path.write_text(json.dumps(coords, indent=2))
print(f"\n좌표 저장 완료! → {path.resolve()}")