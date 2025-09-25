import os
from pathlib import Path

TARGET_DIR = Path("./eeg_data/1번부터 3번")

def rename_eeg_files(directory: Path):
    """
    지정된 디렉토리 내의 EEG 파일 이름을 규칙에 따라 변경합니다.
    - _Q1_ -> _Q21_
    - _Q2_ -> _Q22_
    - _Q3_ -> _Q23_
    """
    if not directory.is_dir():
        print(f"오류: '{directory}' 폴더를 찾을 수 없습니다. TARGET_DIR 경로를 확인해주세요.")
        return

    print(f"'{directory}' 폴더에서 파일 이름 변경을 시작합니다...")

    rename_rules = {
        "_Q1_": "_Q21_",
        "_Q2_": "_Q22_",
        "_Q3_": "_Q23_",
    }

    for old_path in directory.iterdir():
        # 파일인 경우에만 처리
        if old_path.is_file():
            old_name = old_path.name
            new_name = old_name

            # 각 규칙에 대해 파일 이름 변경 시도
            for old_str, new_str in rename_rules.items():
                if old_str in new_name:
                    new_name = new_name.replace(old_str, new_str)
            
            # 파일 이름이 변경되었다면, 실제 파일 이름 변경 실행
            if new_name != old_name:
                new_path = directory / new_name
                try:
                    old_path.rename(new_path)
                    print(f"  ✅ {old_name}  ->  {new_name}")
                except OSError as e:
                    print(f"  ❌ '{old_name}' 이름 변경 실패: {e}")

    print("\n작업 완료.")

if __name__ == "__main__":
    rename_eeg_files(TARGET_DIR)

