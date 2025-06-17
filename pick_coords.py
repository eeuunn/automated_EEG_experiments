# pick_coords.py ― Telescan 전용 좌표 수집기
import pyautogui, time, json, pathlib

print("★ 5초 안에 Telescan 창으로 이동해 주세요 …")
time.sleep(5)

# ▶ 필요한 좌표 키 목록 (순서대로 찍습니다)
KEYS = [
    "REC_START",     # 녹화 시작 버튼
    "REC_STOP",      # Stop 버튼
    "FILENAME_BOX",  # 파일명 입력 칸
    "PATH_BAR",      # 저장창 상단 경로(주소) 바
    "DESKTOP_BTN",   # 왼쪽 탐색 트리뷰의 '바탕화면' 항목
    "SAVE_BUTTON"    # 최종 저장 버튼
]

coords = {}
for key in KEYS:
    print(f"\n▶ {key} 위치로 마우스를 옮긴 뒤 3초만 기다려 주세요 …")
    time.sleep(3)
    x, y = pyautogui.position()
    coords[key] = (x, y)
    print(f"  → {key} 기록 완료: {x}, {y}")

path = pathlib.Path("telescan_coords.json")
path.write_text(json.dumps(coords, indent=2))
print(f"\n좌표 저장 완료! → {path.resolve()}")