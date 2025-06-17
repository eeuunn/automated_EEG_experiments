실험 자동화 시스템 (EEG ‧ 슬라이드 ‧ 컨트롤러)

이 리포지터리는 세 대의 PC(A, B, C) 를 UDP 프로토콜로 연결해 뇌파 실험을 전자동화하기 위한 파이썬 스크립트 모음입니다.
	•	A (EEG PC) : Telescan 녹화·마커 자동화
	•	B (슬라이드 PC) : PowerPoint 슬라이드 진행 자동화
	•	C (컨트롤러 PC) : 시나리오 타이머 + Pygame 상태창 + UDP 브로드캐스트

⸻

📂 디렉터리 구조

experiment/
├─ config.py          # IP·포트·파일 경로 등 중앙 설정
├─ scenario.yaml      # 실험 단계·시간·명령 정의 파일
├─ controller.py      # C – 타이머 & 브로드캐스트
├─ eeg_client.py      # A – Telescan 자동제어
├─ slide_client.py    # B – PowerPoint 자동제어
└─ logs/              # 각 PC가 생성하는 CSV 로그 폴더


⸻

🔧 요구 사항

항목	버전/비고
Python	3.10 이상 (Windows 10/11 테스트 완료)
라이브러리	pygame, pyyaml, pyautogui
네트워크	TP-Link 공유기 환경, UDP 포트 4210 허용
뇌파 소프트웨어	Telescan (단축키: 새 세션 Ctrl+N, 녹화 F5, 정지 F6, 마커 F9)
슬라이드	PowerPoint (슬라이드 쇼 시작 F5, 종료 Esc, 다음 →, 이전 ←)

🛈 단축키·포트·IP 주소는 연구실 환경에 맞춰 config.py 또는 각 스크립트 상단에서 반드시 수정하세요.

⸻

🚀 설치

# 세 대의 PC 모두 동일
pip install pygame pyyaml pyautogui

	1.	고정 IP : config.py 의 A_IP, B_IP 값을 각 PC 주소로 설정합니다.
	2.	방화벽 : TCP/UDP 4210 포트를 인바운드로 허용합니다.
	3.	Telescan / PowerPoint 단축키 : 연구실 키맵과 다르면 eeg_client.py, slide_client.py 의 함수들을 수정합니다.

⸻

▶️ 실행 순서

단계	PC	명령
1	A	python eeg_client.py
2	B	python slide_client.py
3	C	python controller.py

controller.py 는 기본으로 scenario.yaml 을 읽어 타이머를 시작합니다. 다른 시나리오 파일을 쓰려면 python controller.py --file custom.yaml 과 같이 옵션을 주면 됩니다.

실행이 시작되면 C PC 화면에 진행 단계 + 남은 시간 이 Pygame 창으로 표시되고, A·B PC 는 수신한 명령에 따라 자동 동작합니다.

⸻

📝 시나리오 편집 (scenario.yaml)

# name : 단계 이름
# dur  : 초 단위 지속시간(실수 가능)
# send : [대상:명령, ...]  대상 A=EEG PC, B=슬라이드 PC
- { name: "시나리오(1문)", dur: 60.3, send: [A:REC_ON,  B:SHOW_START] }
- { name: "선택지1",        dur: 15.3, send: [B:NEXT] }
# ... 중략 ...
- { name: "ITI",           dur: 10.0, send: [A:REC_OFF, B:SHOW_END] }

	•	명령 목록
	•	A : REC_ON, REC_OFF, MARK_RESP (직접 추가 가능)
	•	B : SHOW_START, SHOW_END, NEXT, PREV
	•	단계는 원하는 만큼 추가·삭제할 수 있으며, dur 값으로 정확한 타이밍을 제어합니다.

⸻

⚙️ 커스터마이징 팁

필요 기능	수정 위치
포트 바꾸기	config.py → PORT
실험 중 추가 마커 전송	scenario.yaml 에 A:MARK_XXX 행 추가 후 eeg_client.py 에 함수 매핑
슬라이드 대신 자체 GUI 사용	slide_client.py 를 교체하거나 pygame 기반으로 재작성
진행률 바·알림음	controller.py 의 Pygame 루프에서 구현
UDP 재전송(패킷 유실 대비)	controller.py → send() 함수에 for _ in range(3): 같은 반복 전송 추가


⸻

🛠️ 문제 해결

증상	원인/해결
Pygame 창이 한글 깨짐	시스템에 NanumGothic 폰트 설치 후 FONT 설정 변경
명령이 수신되지 않음	① 방화벽 포트 4210 허용 여부 확인 ② config.py IP 오타?
Telescan 창이 활성화되지 않음	eeg_client.py 첫 줄에 pyautogui.hotkey("alt","tab") 등 포커스 이동 추가
슬라이드가 넘어가지 않음	PowerPoint 슬라이드 쇼 모드(F5)가 실행 중인지 확인


⸻

📜 라이선스

MIT License – 자유롭게 수정/재배포 가능. 다만 실제 실험에 적용하기 전 안전성 테스트 를 충분히 진행하세요.

© 2025 Kangwon Science High School BCI Lab / Author: Eunwoo Chae & Contributors