# -*- coding: utf-8 -*-
"""
YLIA BookMaker — Nothing Design System & Industrial Instrument Console
PySide6 기반 정밀 계측기 감성 도서 출판 자동화 데스크톱 인터페이스
"""

import os
import sys
import tempfile
import subprocess
import threading
from pathlib import Path

# Windows UTF-8 보장
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PySide6.QtCore import Qt, QSize, Signal, QObject, QPoint
from PySide6.QtGui import QFont, QIcon, QColor, QPixmap, QPainter, QPen, QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QRadioButton, QCheckBox,
    QProgressBar, QTextEdit, QFileDialog, QMessageBox, QFrame,
    QButtonGroup, QSizePolicy
)

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
STYLES_DIR = BASE_DIR / "styles"

# Nothing Design 시그니처 체크마크 생성 (4.8px Bold White Checkmark)
def create_nothing_check_icon() -> str:
    icon_path = os.path.join(tempfile.gettempdir(), "nothing_bookmaker_check.png").replace("\\", "/")
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor("#FFFFFF"), 4.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline([QPoint(7, 16), QPoint(13, 23), QPoint(25, 9)])
    painter.end()
    pixmap.save(icon_path)
    return icon_path

class BuildWorkerSignals(QObject):
    log_received = Signal(str)
    finished = Signal(bool)

class NothingBookMakerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YLIA BookMaker — 도서 출판 제작 콘솔")
        self.resize(920, 980)
        self.setMinimumSize(820, 860)
        self.setAcceptDrops(True)
        
        self.signals = BuildWorkerSignals()
        self.signals.log_received.connect(self.append_log)
        self.signals.finished.connect(self.on_build_finished)
        
        self.is_building = False
        self.default_manuscript = BASE_DIR / "sample_manuscript.md"
        
        self.init_ui()
        self.apply_nothing_stylesheet()
        self.update_kpi_cards()

    def init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(28, 24, 28, 24)
        main_layout.setSpacing(18)

        # ----------------------------------------------------
        # 1. 헤더: 시그니처 레드 도트 + 계측기 타이틀
        # ----------------------------------------------------
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 6)
        
        title_box = QHBoxLayout()
        title_box.setSpacing(12)
        
        dot_label = QLabel("●")
        dot_label.setObjectName("redDot")
        title_box.addWidget(dot_label)
        
        title_label = QLabel("도서 출판 제작 콘솔")
        title_label.setObjectName("mainTitle")
        title_box.addWidget(title_label)
        
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        
        self.status_badge = QLabel("대기 중 // 준비 완료")
        self.status_badge.setObjectName("statusBadge")
        header_layout.addWidget(self.status_badge)
        
        main_layout.addWidget(header_frame)

        # ----------------------------------------------------
        # 2. 계측기 KPI 요약 카드 (Nothing Instrument Panel)
        # ----------------------------------------------------
        kpi_frame = QFrame()
        kpi_frame.setObjectName("kpiFrame")
        kpi_layout = QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(16, 14, 16, 14)
        kpi_layout.setSpacing(14)

        self.kpi_file = self.create_kpi_card("원고 문서", "선택 대기")
        self.kpi_size = self.create_kpi_card("출판 규격", "A5 단행본")
        self.kpi_font = self.create_kpi_card("본문 서체", "현대 고딕체")
        self.kpi_engine = self.create_kpi_card("조판 엔진", "Pandoc 3.12")

        kpi_layout.addWidget(self.kpi_file)
        kpi_layout.addWidget(self.kpi_size)
        kpi_layout.addWidget(self.kpi_font)
        kpi_layout.addWidget(self.kpi_engine)
        
        main_layout.addWidget(kpi_frame)

        # ----------------------------------------------------
        # 3. 1구역: 원고 문서 파일 선택
        # ----------------------------------------------------
        section1 = QFrame()
        section1.setObjectName("cardSection")
        sec1_layout = QVBoxLayout(section1)
        sec1_layout.setContentsMargins(20, 18, 20, 18)
        sec1_layout.setSpacing(10)

        sec1_title = QLabel("1. 원고 문서 파일 선택")
        sec1_title.setObjectName("sectionTitle")
        sec1_layout.addWidget(sec1_title)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)
        
        self.path_input = QLineEdit(str(self.default_manuscript))
        self.path_input.setObjectName("pathInput")
        self.path_input.setPlaceholderText("Markdown (.md) 또는 Word (.docx) 원고 파일을 끌어다 놓으세요")
        self.path_input.textChanged.connect(self.update_kpi_cards)
        file_row.addWidget(self.path_input, stretch=1)

        btn_browse = QPushButton("파일 찾기")
        btn_browse.setObjectName("secondaryBtn")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self.browse_file)
        file_row.addWidget(btn_browse)

        sec1_layout.addLayout(file_row)
        
        hint_label = QLabel("※ 파일을 이 창 위로 직접 끌어다 놓아도(드래그 앤 드롭) 바로 등록됩니다.")
        hint_label.setObjectName("hintLabel")
        sec1_layout.addWidget(hint_label)

        main_layout.addWidget(section1)

        # ----------------------------------------------------
        # 4. 2구역: 출판 규격 및 서체 설정
        # ----------------------------------------------------
        section2 = QFrame()
        section2.setObjectName("cardSection")
        sec2_layout = QVBoxLayout(section2)
        sec2_layout.setContentsMargins(20, 18, 20, 18)
        sec2_layout.setSpacing(14)

        sec2_title = QLabel("2. 도서 조판 및 출력 설정")
        sec2_title.setObjectName("sectionTitle")
        sec2_layout.addWidget(sec2_title)

        # 판형 체크박스 배타적 그룹
        size_layout = QHBoxLayout()
        size_layout.setSpacing(16)
        size_header = QLabel("도서 규격")
        size_header.setObjectName("subSectionHeader")
        size_layout.addWidget(size_header)

        self.size_group = QButtonGroup(self)
        self.size_group.setExclusive(True)
        self.cb_a5 = QCheckBox("A5 (단행본 / 148×210mm)")
        self.cb_b5 = QCheckBox("B5 (교재·참고서 / 182×257mm)")
        self.cb_a4 = QCheckBox("A4 (보고서·매뉴얼 / 210×297mm)")
        self.cb_a5.setChecked(True)

        for cb in (self.cb_a5, self.cb_b5, self.cb_a4):
            self.size_group.addButton(cb)
            size_layout.addWidget(cb)
            cb.toggled.connect(self.update_kpi_cards)
        size_layout.addStretch()
        sec2_layout.addLayout(size_layout)

        # 서체 체크박스 배타적 그룹
        font_layout = QHBoxLayout()
        font_layout.setSpacing(16)
        font_header = QLabel("본문 서체")
        font_header.setObjectName("subSectionHeader")
        font_layout.addWidget(font_header)

        self.font_group = QButtonGroup(self)
        self.font_group.setExclusive(True)
        self.cb_gothic = QCheckBox("고딕체 (맑은 고딕 / 본고딕 계열)")
        self.cb_myeongjo = QCheckBox("명조체 (바탕 / KoPub 바탕 계열)")
        self.cb_gothic.setChecked(True)

        for cb in (self.cb_gothic, self.cb_myeongjo):
            self.font_group.addButton(cb)
            font_layout.addWidget(cb)
            cb.toggled.connect(self.update_kpi_cards)
        font_layout.addStretch()
        sec2_layout.addLayout(font_layout)

        # 출력 포맷 체크박스
        fmt_layout = QHBoxLayout()
        fmt_layout.setSpacing(20)
        fmt_header = QLabel("출력 포맷")
        fmt_header.setObjectName("subSectionHeader")
        fmt_layout.addWidget(fmt_header)

        self.cb_pdf = QCheckBox("인쇄용 PDF (고해상도 제본 규격)")
        self.cb_epub = QCheckBox("표준 전자책 (EPUB3)")
        self.cb_html = QCheckBox("웹 뷰어 (HTML)")
        self.cb_pdf.setChecked(True)
        self.cb_epub.setChecked(True)
        self.cb_html.setChecked(True)

        fmt_layout.addWidget(self.cb_pdf)
        fmt_layout.addWidget(self.cb_epub)
        fmt_layout.addWidget(self.cb_html)
        fmt_layout.addStretch()
        sec2_layout.addLayout(fmt_layout)

        main_layout.addWidget(section2)

        # ----------------------------------------------------
        # 5. 메인 실행 버튼 (Hero Run Button) & 프로그레스
        # ----------------------------------------------------
        self.btn_run = QPushButton("도서 출판 제작 실행")
        self.btn_run.setObjectName("heroRunBtn")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_run.clicked.connect(self.start_build)
        main_layout.addWidget(self.btn_run)

        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("nothingProgress")
        self.progress_bar.setRange(0, 0) # 무한 펄스
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # ----------------------------------------------------
        # 6. 시스템 작업 기록 콘솔 (Console Log)
        # ----------------------------------------------------
        log_section = QFrame()
        log_section.setObjectName("cardSection")
        log_layout = QVBoxLayout(log_section)
        log_layout.setContentsMargins(18, 14, 18, 14)
        log_layout.setSpacing(8)

        log_header = QLabel("시스템 실시간 작업 기록")
        log_header.setObjectName("sectionTitle")
        log_layout.addWidget(log_header)

        self.console = QTextEdit()
        self.console.setObjectName("consoleOutput")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(130)
        log_layout.addWidget(self.console)

        main_layout.addWidget(log_section)

        # ----------------------------------------------------
        # 7. 출력 결과물 퀵 액션 도구바
        # ----------------------------------------------------
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.btn_open_pdf = QPushButton("인쇄본 PDF 열기")
        self.btn_open_pdf.setObjectName("actionBtn")
        self.btn_open_pdf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_pdf.clicked.connect(self.open_pdf)
        action_bar.addWidget(self.btn_open_pdf)

        self.btn_open_epub = QPushButton("EPUB 전자책 확인")
        self.btn_open_epub.setObjectName("actionBtn")
        self.btn_open_epub.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_epub.clicked.connect(self.open_epub)
        action_bar.addWidget(self.btn_open_epub)

        self.btn_open_html = QPushButton("웹 HTML 보기")
        self.btn_open_html.setObjectName("actionBtn")
        self.btn_open_html.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_html.clicked.connect(self.open_html)
        action_bar.addWidget(self.btn_open_html)

        self.btn_open_folder = QPushButton("출력 폴더 열기")
        self.btn_open_folder.setObjectName("actionBtn")
        self.btn_open_folder.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_open_folder.clicked.connect(self.open_output_folder)
        action_bar.addWidget(self.btn_open_folder)

        main_layout.addLayout(action_bar)
        
        self.append_log("시스템 준비 완료: 원고 파일을 지정하고 [도서 출판 제작 실행]을 누르세요.")

    def create_kpi_card(self, title_text: str, value_text: str) -> QFrame:
        card = QFrame()
        card.setObjectName("kpiCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        t_lbl = QLabel(title_text)
        t_lbl.setObjectName("kpiTitle")
        layout.addWidget(t_lbl)

        v_lbl = QLabel(value_text)
        v_lbl.setObjectName("kpiValue")
        layout.addWidget(v_lbl)
        
        card.value_label = v_lbl
        return card

    def update_kpi_cards(self):
        # 파일명 및 용량
        fpath = Path(self.path_input.text().strip())
        if fpath.exists():
            size_kb = fpath.stat().st_size // 1024
            name = fpath.name if len(fpath.name) <= 16 else fpath.name[:14] + "…"
            self.kpi_file.value_label.setText(f"{name} ({size_kb}KB)")
        else:
            self.kpi_file.value_label.setText("파일 없음")

        # 판형
        if self.cb_a5.isChecked():
            self.kpi_size.value_label.setText("A5 단행본")
        elif self.cb_b5.isChecked():
            self.kpi_size.value_label.setText("B5 교재")
        else:
            self.kpi_size.value_label.setText("A4 보고서")

        # 서체
        if self.cb_gothic.isChecked():
            self.kpi_font.value_label.setText("현대 고딕체")
        else:
            self.kpi_font.value_label.setText("전통 명조체")

    def append_log(self, text: str):
        self.console.append(text)
        self.console.verticalScrollBar().setValue(self.console.verticalScrollBar().maximum())

    def browse_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self,
            "원고 문서 파일 선택",
            str(BASE_DIR),
            "지원 원고 파일 (*.md *.markdown *.docx *.txt);;마크다운 (*.md);;Word 문서 (*.docx);;모든 파일 (*.*)"
        )
        if f:
            self.path_input.setText(f)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            local_path = urls[0].toLocalFile()
            if local_path:
                self.path_input.setText(local_path)
                event.acceptProposedAction()

    def update_css_for_build(self):
        size = "A5"
        if self.cb_b5.isChecked():
            size = "B5"
        elif self.cb_a4.isChecked():
            size = "A4"

        font_str = "'Pretendard', 'Noto Sans KR', 'Malgun Gothic', sans-serif"
        if self.cb_myeongjo.isChecked():
            font_str = "'Batang', 'KoPubWorld Batang', 'Source Han Serif K', 'Noto Serif KR', serif"

        print_css_path = STYLES_DIR / "print.css"
        if print_css_path.exists():
            content = print_css_path.read_text(encoding="utf-8")
            import re
            content = re.sub(r'size:\s*[A-Za-z0-9]+;', f'size: {size};', content)
            content = re.sub(r"font-family:\s*[^;]+;", f"font-family: {font_str};", content, count=1)
            print_css_path.write_text(content, encoding="utf-8")

    def start_build(self):
        if self.is_building:
            return

        input_path = Path(self.path_input.text().strip())
        if not input_path.exists():
            QMessageBox.critical(self, "원고 파일 오류", f"지정한 원고 파일을 찾을 수 없습니다:\n{input_path}")
            return

        self.is_building = True
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_badge.setText("제작 진행 중 // 컴파일")
        self.status_badge.setStyleSheet("background-color: #FEF2F2; color: #D71921; border-color: #F87171;")
        
        self.console.clear()
        self.append_log(f"============================================================")
        self.append_log(f"  ● YLIA BookMaker: 도서 제작 프로세스를 가동합니다")
        self.append_log(f"  - 원고: {input_path.name}")
        self.append_log(f"  - 판형: {self.kpi_size.value_label.text()}")
        self.append_log(f"  - 서체: {self.kpi_font.value_label.text()}")
        self.append_log(f"============================================================")

        threading.Thread(target=self.build_thread_worker, args=(input_path,), daemon=True).start()

    def build_thread_worker(self, input_path: Path):
        try:
            self.update_css_for_build()
            script_path = BASE_DIR / "bookmaker.py"
            cmd = [sys.executable, str(script_path), str(input_path)]
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )
            for line in proc.stdout:
                line_str = line.strip()
                if line_str:
                    self.signals.log_received.emit(line_str)
            proc.wait()
            self.signals.finished.emit(proc.returncode == 0)
        except Exception as e:
            self.signals.log_received.emit(f"[오류 발생] {e}")
            self.signals.finished.emit(False)

    def on_build_finished(self, success: bool):
        self.is_building = False
        self.btn_run.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            self.status_badge.setText("제작 완료 // 정상 출력")
            self.status_badge.setStyleSheet("background-color: #F0FDF4; color: #16A34A; border-color: #86EFAC;")
            self.append_log("\n[완료] 모든 출판 파일 빌드가 무결하게 완료되었습니다. 🎉")
            QMessageBox.information(self, "출판 제작 완료", "도서 파일(PDF, EPUB, HTML) 생성이 성공적으로 완료되었습니다!")
        else:
            self.status_badge.setText("오류 발생 // 확인 요망")
            self.status_badge.setStyleSheet("background-color: #FEF2F2; color: #DC2626; border-color: #FCA5A5;")
            self.append_log("\n[실패] 도서 제작 중 오류가 발생했습니다. 로그를 검토하세요.")
            QMessageBox.warning(self, "제작 실패", "도서 빌드 중 오류가 발생했습니다.")

    def open_pdf(self):
        p = Path(self.path_input.text().strip())
        target = OUTPUT_DIR / f"{p.stem}.pdf"
        if target.exists():
            os.startfile(str(target))
        else:
            QMessageBox.information(self, "알림", "생성된 PDF 파일이 없습니다. 먼저 도서 제작을 실행하세요.")

    def open_epub(self):
        p = Path(self.path_input.text().strip())
        target = OUTPUT_DIR / f"{p.stem}.epub"
        if target.exists():
            os.startfile(str(target))
        else:
            QMessageBox.information(self, "알림", "생성된 EPUB 파일이 없습니다. 먼저 도서 제작을 실행하세요.")

    def open_html(self):
        p = Path(self.path_input.text().strip())
        target = OUTPUT_DIR / f"{p.stem}.html"
        if target.exists():
            os.startfile(str(target))
        else:
            QMessageBox.information(self, "알림", "생성된 HTML 파일이 없습니다. 먼저 도서 제작을 실행하세요.")

    def open_output_folder(self):
        if OUTPUT_DIR.exists():
            os.startfile(str(OUTPUT_DIR))
        else:
            QMessageBox.information(self, "알림", "output 폴더가 아직 생성되지 않았습니다.")

    def apply_nothing_stylesheet(self):
        check_icon_path = create_nothing_check_icon()
        qss = f"""
        /* 글로벌 베이스 (Nothing Minimal Slate) */
        QWidget#centralWidget {{
            background-color: #F8FAFC;
        }}
        
        QWidget {{
            font-family: "강원교육모두", "GangwonEduAll", "Pretendard", "Malgun Gothic", sans-serif;
            font-size: 18px;
            font-weight: bold;
            color: #0F172A;
        }}

        /* 헤더 스타일 */
        QLabel#redDot {{
            color: #D71921;
            font-size: 26px;
            font-weight: 900;
        }}
        QLabel#mainTitle {{
            font-size: 29px;
            font-weight: 800;
            color: #0F172A;
            letter-spacing: -0.5px;
        }}
        QLabel#statusBadge {{
            font-size: 17px;
            font-weight: 700;
            padding: 7px 16px;
            border-radius: 8px;
            border: 1px solid #CBD5E1;
            background-color: #FFFFFF;
            color: #475569;
        }}

        /* 계측기 KPI 카드 */
        QFrame#kpiFrame {{
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
        }}
        QFrame#kpiCard {{
            background-color: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 8px;
        }}
        QLabel#kpiTitle {{
            font-size: 16px;
            font-weight: 700;
            color: #64748B;
        }}
        QLabel#kpiValue {{
            font-size: 20px;
            font-weight: 800;
            color: #0F172A;
        }}

        /* 섹션 카드 */
        QFrame#cardSection {{
            background-color: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
        }}
        QLabel#sectionTitle {{
            font-size: 21px;
            font-weight: 800;
            color: #0F172A;
        }}
        QLabel#subSectionHeader {{
            font-size: 18px;
            font-weight: 700;
            color: #334155;
            min-width: 85px;
        }}
        QLabel#hintLabel {{
            font-size: 16px;
            color: #64748B;
        }}

        /* 입력 필드 */
        QLineEdit#pathInput {{
            height: 54px;
            padding: 0 18px;
            font-size: 18px;
            background-color: #FFFFFF;
            border: 2px solid #E2E8F0;
            border-radius: 10px;
            color: #0F172A;
        }}
        QLineEdit#pathInput:focus {{
            border: 2px solid #0F172A;
        }}

        /* 보조 버튼 */
        QPushButton#secondaryBtn {{
            height: 54px;
            padding: 0 26px;
            font-size: 18px;
            font-weight: 700;
            background-color: #0F172A;
            color: #FFFFFF;
            border-radius: 10px;
            border: none;
        }}
        QPushButton#secondaryBtn:hover {{
            background-color: #D71921;
        }}

        /* 고대비 라디오 버튼 */
        QRadioButton {{
            spacing: 10px;
            font-size: 18px;
            font-weight: 600;
            color: #1E293B;
        }}
        QRadioButton::indicator {{
            width: 24px;
            height: 24px;
            border-radius: 12px;
            border: 2px solid #94A3B8;
            background-color: #FFFFFF;
        }}
        QRadioButton::indicator:hover {{
            border-color: #0F172A;
        }}
        QRadioButton::indicator:checked {{
            background-color: #0F172A;
            border: 6px solid #FFFFFF;
            outline: 2px solid #0F172A;
        }}

        /* 고대비 체크박스 (Nothing High-Contrast Solid Indicator) */
        QCheckBox {{
            spacing: 10px;
            font-size: 18px;
            font-weight: 600;
            color: #1E293B;
        }}
        QCheckBox::indicator {{
            width: 24px;
            height: 24px;
            border-radius: 6px;
            border: 2px solid #94A3B8;
            background-color: #FFFFFF;
        }}
        QCheckBox::indicator:hover {{
            border-color: #0F172A;
            background-color: #F1F5F9;
        }}
        QCheckBox::indicator:checked {{
            background-color: #0F172A;
            border: 2px solid #0F172A;
            image: url('{check_icon_path}');
        }}

        /* 히어로 실행 버튼 */
        QPushButton#heroRunBtn {{
            height: 64px;
            font-size: 22px;
            font-weight: 800;
            background-color: #0F172A;
            color: #FFFFFF;
            border-radius: 12px;
            border: none;
            letter-spacing: 0.5px;
        }}
        QPushButton#heroRunBtn:hover {{
            background-color: #D71921;
        }}
        QPushButton#heroRunBtn:disabled {{
            background-color: #94A3B8;
        }}

        /* 프로그레스 바 */
        QProgressBar#nothingProgress {{
            height: 10px;
            background-color: #E2E8F0;
            border-radius: 5px;
            text-align: center;
        }}
        QProgressBar#nothingProgress::chunk {{
            background-color: #D71921;
            border-radius: 5px;
        }}

        /* 시스템 콘솔 출력창 */
        QTextEdit#consoleOutput {{
            background-color: #0F172A;
            color: #F8FAFC;
            font-family: "Consolas", "D2Coding", monospace;
            font-size: 17px;
            line-height: 1.5;
            border: 1px solid #1E293B;
            border-radius: 8px;
            padding: 12px;
        }}

        /* 하단 액션 툴바 버튼 */
        QPushButton#actionBtn {{
            height: 52px;
            font-size: 18px;
            font-weight: 700;
            background-color: #FFFFFF;
            color: #0F172A;
            border: 1px solid #CBD5E1;
            border-radius: 10px;
            padding: 0 14px;
        }}
        QPushButton#actionBtn:hover {{
            background-color: #F1F5F9;
            border-color: #0F172A;
        }}
        """
        self.setStyleSheet(qss)

def main():
    app = QApplication(sys.argv)
    
    # 강원교육모두 Bold 전역 폰트 적용 (2단계 상향: 14pt)
    font = QFont("강원교육모두")
    if not font.exactMatch():
        font = QFont("GangwonEduAll")
    if not font.exactMatch():
        font = QFont("Malgun Gothic")
    font.setBold(True)
    font.setPointSize(14) # HiDPI 포인트 스케일 (기존 12pt -> 14pt)
    app.setFont(font)

    window = NothingBookMakerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
