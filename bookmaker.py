# -*- coding: utf-8 -*-
"""
YLIA BookMaker - Modern Publishing Pipeline
Pandoc + CSS Paged Media (Playwright / Chromium Engine) 기반 원클릭 도서 출판 빌더
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

# Windows UTF-8 콘솔 출력 보장
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
STYLES_DIR = BASE_DIR / "styles"

# Pandoc 실행 파일 탐색
def find_pandoc():
    # PATH 우선 확인
    pandoc_cmd = shutil.which("pandoc")
    if pandoc_cmd:
        return pandoc_cmd
    
    # 윈도우 LocalAppData 경로 확인
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        candidate = Path(local_app_data) / "Pandoc" / "pandoc.exe"
        if candidate.exists():
            return str(candidate)
            
    # Program Files 확인
    candidate_pf = Path("C:/Program Files/Pandoc/pandoc.exe")
    if candidate_pf.exists():
        return str(candidate_pf)
        
    return None

# 브라우저 기반 Headless PDF 인쇄 (CSS Paged Media 완벽 지원)
def convert_html_to_pdf_via_browser(html_path: Path, pdf_path: Path):
    # 1순위: Playwright 사용 시도
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(html_path.as_uri())
            # A5 판형 및 인쇄 배경 포함 PDF 생성
            page.pdf(
                path=str(pdf_path),
                format="A5",
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "0mm", "bottom": "0mm", "left": "0mm", "right": "0mm"}
            )
            browser.close()
            return True
    except Exception as e:
        pass

    # 2순위: 시스템에 설치된 MS Edge 또는 Chrome 헤드리스 CLI 호출
    browser_candidates = [
        Path("C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Microsoft/Edge/Application/msedge.exe"),
        Path("C:/Program Files/Google/Chrome/Application/chrome.exe"),
        Path("C:/Program Files (x86)/Google/Chrome/Application/chrome.exe"),
    ]
    
    for browser_exe in browser_candidates:
        if browser_exe.exists():
            cmd = [
                str(browser_exe),
                "--headless=new",
                "--disable-gpu",
                "--run-all-compositor-stages-before-draw",
                f"--print-to-pdf={pdf_path}",
                str(html_path)
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                return True

    return False

def build_book(input_file: Path):
    if not input_file.exists():
        print(f"[오류] 원고 파일을 찾을 수 없습니다: {input_file}")
        return False

    pandoc = find_pandoc()
    if not pandoc:
        print("[오류] Pandoc 실행 파일을 찾을 수 없습니다. Pandoc 설치 여부를 확인하세요.")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = input_file.stem
    
    epub_out = OUTPUT_DIR / f"{stem}.epub"
    html_out = OUTPUT_DIR / f"{stem}.html"
    pdf_out = OUTPUT_DIR / f"{stem}.pdf"

    print("=" * 60)
    print(f"  📖 YLIA BookMaker: 도서 빌드를 시작합니다")
    print(f"  - 원고: {input_file.name}")
    print(f"  - 엔진: Pandoc ({pandoc})")
    print("=" * 60)

    # 1. EPUB 생성
    print("\n[1/3] EPUB 전자책 생성 중...")
    epub_cmd = [
        pandoc,
        str(input_file),
        "-o", str(epub_out),
        "--toc",
        "--toc-depth=2",
        "--epub-chapter-level=1"
    ]
    epub_css = STYLES_DIR / "epub.css"
    if epub_css.exists():
        epub_cmd.extend(["--css", str(epub_css)])

    res_epub = subprocess.run(epub_cmd, capture_output=True, text=True)
    if res_epub.returncode == 0:
        print(f"  ✓ EPUB 생성 완료: {epub_out.name} ({epub_out.stat().st_size // 1024} KB)")
    else:
        print(f"  ✗ EPUB 생성 실패:\n{res_epub.stderr}")

    # 2. 인쇄 준비용 HTML 생성
    print("\n[2/3] 출판 조판용 HTML 생성 중...")
    html_cmd = [
        pandoc,
        str(input_file),
        "-o", str(html_out),
        "--standalone",
        "--toc",
        "--toc-depth=2"
    ]
    print_css = STYLES_DIR / "print.css"
    if print_css.exists():
        html_cmd.extend(["--css", str(print_css)])

    res_html = subprocess.run(html_cmd, capture_output=True, text=True)
    if res_html.returncode == 0:
        print(f"  ✓ HTML 생성 완료: {html_out.name} ({html_out.stat().st_size // 1024} KB)")
    else:
        print(f"  ✗ HTML 생성 실패:\n{res_html.stderr}")

    # 3. 출판용 PDF 생성 (CSS Paged Media 렌더링)
    print("\n[3/3] 인쇄용 고해상도 PDF 생성 중 (CSS Paged Media)...")
    if html_out.exists():
        success_pdf = convert_html_to_pdf_via_browser(html_out, pdf_out)
        if success_pdf and pdf_out.exists():
            print(f"  ✓ PDF 조판 완료: {pdf_out.name} ({pdf_out.stat().st_size // 1024} KB)")
        else:
            print("  ✗ PDF 생성 실패: 브라우저 렌더링 엔진 호출에 실패했습니다.")

    print("\n" + "=" * 60)
    print("  🎉 모든 출판 파일 빌드가 완료되었습니다!")
    print(f"  📁 출력 디렉터리: {OUTPUT_DIR}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    target = BASE_DIR / "sample_manuscript.md"
    if len(sys.argv) > 1:
        target = Path(sys.argv[1]).resolve()
    build_book(target)
