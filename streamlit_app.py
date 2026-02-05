import streamlit as st
import streamlit.components.v1 as components
import os

# 페이지 기본 설정 (화면을 넓게 씀)
st.set_page_config(layout="wide", page_title="콘홀 프로그램 (Porting Ver)")

def load_html_file():
    """index.html 파일을 읽어서 문자열로 반환합니다."""
    # 현재 폴더에 있는 index.html을 찾습니다.
    file_path = os.path.join(os.path.dirname(__file__), 'index.html')
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return html_content
    except FileNotFoundError:
        st.error("❌ 'index.html' 파일을 찾을 수 없습니다. 같은 폴더에 넣어주세요.")
        return None

# --- 메인 화면 ---
st.title("📂 기존 콘홀 프로그램 (Streamlit Porting)")
st.caption("기존 웹 프로그램(HTML/JS)을 Streamlit 환경에서 실행 중입니다.")

# 1. HTML 파일 읽기
html_code = load_html_file()

# 2. 화면에 표시하기
if html_code:
    # height는 프로그램 길이에 맞춰서 조절하세요 (예: 800, 1000)
    components.html(html_code, height=1000, scrolling=True)

# --- (향후 개발 예정 영역) ---
st.divider()
st.info("ℹ️ 추후 이곳에 파이썬 기반의 '크롤링 기능'과 '자동 대진표 생성' 기능이 결합될 예정입니다.")