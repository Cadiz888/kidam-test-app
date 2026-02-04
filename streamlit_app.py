import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import random
import matplotlib.pyplot as plt
from matplotlib import rc
import io
import matplotlib.font_manager as fm

# --- 0. 설정: 한글 폰트 (Streamlit Cloud 호환) ---
# 리눅스 서버(Streamlit Cloud)에서 한글 깨짐 방지
try:
    # 폰트 설치가 되어 있다고 가정 ('packages.txt' 이용)
    plt.rc('font', family='NanumGothic') 
    plt.rcParams['axes.unicode_minus'] = False
except:
    pass

st.set_page_config(page_title="콘홀 스마트 대진표", layout="wide")

# --- 1. 핵심 로직 (크롤링 & 데이터 처리) ---
@st.cache_data(ttl=600) # 10분간 캐시 유지
def fetch_rankings_logic():
    url = "https://cornhole.kr/html/sub5_1.jsp"
    headers = {'User-Agent': 'Mozilla/5.0'}
    ranking_dict = {}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 2:
                    text_data = [ele.get_text(strip=True) for ele in cols]
                    name = None
                    score = 0
                    for text in text_data:
                        if re.match(r'^[가-힣]{2,4}$', text):
                            if text not in ['선수', '이름', '성명', '순위']:
                                name = text
                                break
                    if name:
                        for text in text_data:
                            if text == name: continue
                            score_match = re.search(r'([\d,]+)\s*(pts|점|point)', text, re.IGNORECASE)
                            if score_match:
                                try:
                                    s = int(score_match.group(1).replace(',', ''))
                                    score = max(score, s)
                                except: pass
                            elif text.replace(',', '').isdigit():
                                try:
                                    s = int(text.replace(',', ''))
                                    if s > score: score = s
                                except: pass
                        if score > 0: ranking_dict[name] = score
        return ranking_dict
    except:
        return {}

def draw_bracket(match_list, title):
    fig, ax = plt.subplots(figsize=(8, 10))
    ax.set_title(title, fontsize=15, pad=10)
    ax.axis('off')
    
    y_pos = [16, 14, 12, 10, 8, 6, 4, 2]
    for i, match in enumerate(match_list):
        if i >= len(y_pos): break # 16강 초과 시 예외처리
        y = y_pos[i]
        p1, t1, s1 = match['Player 1'], match['Team 1'], match['Score 1']
        p2, t2, s2 = match['Player 2'], match['Team 2'], match['Score 2']
        
        if p2 == 'BYE':
            p1_txt = f"⭐ {p1}\n({t1}/{s1})"
            p2_txt = "(부전승)"
            col = 'blue'
        else:
            p1_txt = f"{p1}\n({t1}/{s1})"
            p2_txt = f"{p2}\n({t2}/{s2})"
            col = 'black'

        ax.plot([1, 3], [y+0.6, y+0.6], color=col, lw=1)
        ax.plot([1, 3], [y-0.6, y-0.6], 'k-', lw=1)
        ax.plot([3, 3], [y+0.6, y-0.6], 'k-', lw=1)
        ax.plot([3, 4], [y, y], 'k-', lw=1)
        ax.text(0.9, y+0.6, p1_txt, ha='right', va='center', fontsize=9, fontweight='bold')
        ax.text(0.9, y-0.6, p2_txt, ha='right', va='center', fontsize=9)
        ax.text(3.5, y+0.2, f"M{i+1}", ha='center', va='bottom', fontsize=8, color='gray')
    
    plt.tight_layout()
    return fig

# --- 2. 세션 상태 초기화 (데이터 저장소) ---
if 'df_all' not in st.session_state:
    st.session_state.df_all = pd.DataFrame(columns=["이름", "소속", "점수"])
if 'df_ranked' not in st.session_state:
    st.session_state.df_ranked = pd.DataFrame(columns=["이름", "소속", "점수"])
if 'df_unranked' not in st.session_state:
    st.session_state.df_unranked = pd.DataFrame(columns=["이름", "소속", "점수"])

# --- 3. UI 구성 ---
st.title("🏆 콘홀 협회 스마트 대진표 (Web)")

# 사이드바: 컨트롤 패널
with st.sidebar:
    st.header("1. 데이터 입력")
    uploaded_file = st.file_uploader("엑셀 파일 업로드", type=['xlsx', 'csv'])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                try: df = pd.read_csv(uploaded_file, encoding='cp949')
                except: df = pd.read_csv(uploaded_file, encoding='utf-8')
            else:
                df = pd.read_excel(uploaded_file)
            
            df.columns = df.columns.str.strip()
            name_col = next((c for c in df.columns if any(x in c for x in ['이름', '성명', '참가자'])), None)
            team_col = None
            for k in ['소속팀', '팀명', '소속', '팀']:
                found = next((c for c in df.columns if k in c), None)
                if found: 
                    team_col = found
                    break
            
            if name_col:
                new_data = []
                for _, row in df.iterrows():
                    n = str(row[name_col]).strip()
                    t = str(row[team_col]).strip() if (team_col and pd.notna(row[team_col])) else "-"
                    if not t: t = "-"
                    new_data.append({"이름": n, "소속": t, "점수": 0})
                st.session_state.df_all = pd.DataFrame(new_data)
                st.success(f"{len(new_data)}명 로드 완료!")
        except Exception as e:
            st.error(f"파일 읽기 실패: {e}")

    st.header("2. 기능 실행")
    if st.button("🌐 협회 랭킹 점수 조회"):
        with st.spinner("cornhole.kr 조회 중..."):
            rankings = fetch_rankings_logic()
            cnt = 0
            # 전체 탭 기준 업데이트
            for idx, row in st.session_state.df_all.iterrows():
                if row['이름'] in rankings:
                    st.session_state.df_all.at[idx, '점수'] = rankings[row['이름']]
                    cnt += 1
            st.success(f"{cnt}명 점수 업데이트!")

    if st.button("⚡ 랭킹별 조 분리 (A/B)"):
        df = st.session_state.df_all
        if not df.empty:
            df['점수'] = df['점수'].astype(int)
            st.session_state.df_ranked = df[df['점수'] > 0].copy()
            st.session_state.df_unranked = df[df['점수'] == 0].copy()
            st.success(f"A조: {len(st.session_state.df_ranked)}명 / B조: {len(st.session_state.df_unranked)}명 분리 완료")
        else:
            st.warning("데이터가 없습니다.")

    if st.button("🗑️ 전체 초기화"):
        st.session_state.df_all = pd.DataFrame(columns=["이름", "소속", "점수"])
        st.session_state.df_ranked = pd.DataFrame(columns=["이름", "소속", "점수"])
        st.session_state.df_unranked = pd.DataFrame(columns=["이름", "소속", "점수"])
        st.rerun()

# 메인 화면: 탭 구성
tab1, tab2, tab3 = st.tabs(["전체 명단", "A조 (유랭킹)", "B조 (무랭킹)"])

def match_generator_ui(df, tab_name, key_suffix, force_random=False):
    # 데이터 에디터 (수정 가능)
    edited_df = st.data_editor(df, num_rows="dynamic", key=f"editor_{key_suffix}")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("설정")
        if force_random:
            st.info("※ B조는 랜덤 모드가 강제됩니다.")
            mode = "랜덤"
        else:
            mode = st.radio("생성 모드", ["공평 (실력순)", "랜덤 (무작위)"], key=f"mode_{key_suffix}")
        
        if st.button(f"▶ {tab_name} 대진표 생성", key=f"btn_{key_suffix}"):
            if len(edited_df) < 2:
                st.error("최소 2명이 필요합니다.")
            else:
                players = edited_df.to_dict('records')
                # 데이터 타입 정리
                for p in players:
                    try: p['점수'] = int(p['점수'])
                    except: p['점수'] = 0
                
                # 정렬
                if "공평" in mode and not force_random:
                    players.sort(key=lambda x: x['점수'], reverse=True)
                else:
                    random.shuffle(players)
                
                # 대진표 로직
                bracket_size = 16
                seeds = {}
                for i in range(bracket_size):
                    if i < len(players): seeds[i+1] = players[i]
                    else: seeds[i+1] = {'이름': 'BYE', '소속': '-', '점수': '-'}
                
                matchups = [(1, 16), (8, 9), (4, 13), (5, 12), (2, 15), (7, 10), (3, 14), (6, 11)]
                results = []
                for sa, sb in matchups:
                    p1, p2 = seeds[sa], seeds[sb]
                    results.append({
                        'Match': f"S{sa} vs S{sb}",
                        'Player 1': p1['이름'], 'Team 1': p1['소속'], 'Score 1': p1['점수'],
                        'Player 2': p2['이름'], 'Team 2': p2['소속'], 'Score 2': p2['점수']
                    })
                
                # 결과 저장 (세션)
                st.session_state[f'matches_{key_suffix}'] = results
                st.session_state[f'fig_{key_suffix}'] = draw_bracket(results, f"2026 콘홀 {tab_name}")

    with col2:
        st.subheader("미리보기 & 다운로드")
        if f'matches_{key_suffix}' in st.session_state:
            fig = st.session_state[f'fig_{key_suffix}']
            st.pyplot(fig)
            
            # 다운로드 버튼
            # 1. 엑셀
            res_df = pd.DataFrame(st.session_state[f'matches_{key_suffix}'])
            excel_buffer = io.BytesIO()
            res_df.to_excel(excel_buffer, index=False)
            st.download_button("💾 엑셀 다운로드", data=excel_buffer, file_name=f"대진표_{tab_name}.xlsx")
            
            # 2. 이미지
            img_buffer = io.BytesIO()
            fig.savefig(img_buffer, format='png', dpi=300)
            st.download_button("🖼️ 이미지 다운로드", data=img_buffer, file_name=f"대진표_{tab_name}.png", mime="image/png")

# 각 탭에 UI 배치
with tab1:
    match_generator_ui(st.session_state.df_all, "전체", "all")
with tab2:
    match_generator_ui(st.session_state.df_ranked, "A조", "ranked")
with tab3:
    match_generator_ui(st.session_state.df_unranked, "B조", "unranked", force_random=True)