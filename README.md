# YLIA BookMaker

Pandoc과 모던 CSS 엔진 기반의 도서 출판 자동화 및 PySide6 데스크톱 GUI 빌더입니다.

## 주요 기능
- **단일 원고 다중 포맷 출판 (Single-Source Multi-Format)**: Markdown(`.md`) 또는 Word(`.docx`) 원고 하나로 인쇄용 PDF, 표준 전자책(EPUB), 웹 뷰어(HTML)를 동시 빌드
- **CSS Paged Media 규격 조판**: W3C 인쇄 CSS 규격을 활용한 A5/B5/A4 판형, 양면 제본 여백, 자동 페이지 번호 조판
- **Nothing Design & 계측기 감성 데스크톱 GUI**:
  - `강원교육모두 Bold` 타이포그래피 전면 적용
  - 고대비 체크 인디케이터 (솔리드 다크 + 화이트 V 체크마크)
  - 원고 파일 드래그 앤 드롭 지원
  - 4대 출력물(PDF, EPUB, HTML, 폴더) 퀵 액션 도구바

## 프로젝트 구조
```text
BookMaker/
├── bookmaker.py            # 메인 빌드 파이프라인
├── gui.py                  # Nothing Design PySide6 데스크톱 GUI
├── run_gui.bat             # GUI 실행 배치 파일
├── run_gui.vbs             # GUI 백그라운드 실행 런처
├── build.bat               # 원클릭 CLI 빌드 배치 파일
├── sample_manuscript.md    # 샘플 도서 원고
├── styles/
│   ├── print.css           # 인쇄용 CSS Paged Media 스타일시트
│   └── epub.css            # 전자책 전용 반응형 스타일시트
└── output/                 # 최종 출력 파일 디렉터리
```

## 실행 방법
- **GUI 실행**: `run_gui.vbs` 또는 `run_gui.bat` 실행
- **CLI 빌드**: `python bookmaker.py sample_manuscript.md`
