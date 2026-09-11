import os
import time
import json

# .env 파일 로드 (앱 디렉토리 기준). 실행 위치와 무관하게 키가 적용되도록 함.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except Exception:
    pass

import streamlit as st
from rag_engine import CatRAGEngine, DEFAULT_API_KEY, DEFAULT_GEMINI_API_KEY, DEFAULT_DB_PATH
from cat_widget import render_interactive_cat

# -----------------------------------------------------------------------------
# 방문자 수 및 누적 질문 수 영구 통계 관리
# -----------------------------------------------------------------------------
STATS_FILE = os.path.join(os.path.dirname(__file__), "app_stats.json")

def load_app_stats():
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {
                    "visitors": max(1, data.get("visitors", 1)),
                    "questions": max(0, data.get("questions", 0))
                }
    except Exception:
        pass
    return {"visitors": 1, "questions": 0}

def save_app_stats(stats):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def increment_question_count():
    stats = load_app_stats()
    stats["questions"] += 1
    save_app_stats(stats)
    return stats

# -----------------------------------------------------------------------------
# 1. 페이지 설정 & 프리미엄 베이지 웜톤 UI 스타일링
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="KU ScholarCat | 고려대학교 학술·논문 & 멀티툴 AI 비서",
    page_icon="🐾",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 세련된 프론트엔드 스타일 (Pretendard 폰트 + 아늑한 크림 베이지 디자인)
st.markdown("""
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');

    /* 전체 텍스트 타이포그래피 (아이콘 제외) */
    html, body, .stApp, p, h1, h2, h3, h4, h5, h6, input, button, textarea {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
    }
    
    /* Streamlit expander 아이콘 보존 */
    [data-testid="stExpanderToggleIcon"] {
        font-family: inherit !important;
    }

    /* 메인 배경 */
    .stApp {
        background: linear-gradient(145deg, #fdfbf7 0%, #f8f4ec 50%, #f3ede2 100%) !important;
        color: #1c1917 !important;
    }

    /* 사이드바 스타일링 */
    [data-testid="stSidebar"] {
        background: #f7f3ea !important;
        border-right: 1px solid #e8dfd1 !important;
    }

    [data-testid="stSidebar"] * {
        color: #292524 !important;
    }

    /* 메인 히어로 배너 */
    .hero-banner {
        background: linear-gradient(135deg, #ffffff 0%, #fefcf9 60%, #faedd8 100%);
        border: 1.5px solid #e8dfd1;
        border-radius: 20px;
        padding: 26px 32px;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -8px rgba(180, 140, 90, 0.12);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(135deg, #7c2d12 0%, #c2410c 45%, #d97706 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.6px;
    }

    .hero-desc {
        color: #57534e !important;
        font-size: 1.02rem;
        margin-top: 6px;
        font-weight: 500;
    }

    .cat-profile-badge {
        display: flex;
        align-items: center;
        gap: 14px;
        background: #ffffff;
        padding: 10px 20px;
        border-radius: 40px;
        border: 1.5px solid #fed7aa;
        box-shadow: 0 4px 14px rgba(234, 88, 12, 0.1);
    }

    .cat-avatar {
        font-size: 2rem;
    }

    .cat-badge-title {
        font-size: 0.95rem;
        font-weight: 800;
        color: #9a3412 !important;
    }

    .cat-badge-sub {
        font-size: 0.78rem;
        color: #16a34a !important;
        font-weight: 700;
    }

    /* 채팅 카드 디자인 */
    .user-card {
        background: #ffffff;
        border: 1px solid #fed7aa;
        border-left: 4px solid #ea580c;
        border-radius: 14px;
        padding: 16px 20px;
        margin-bottom: 8px;
        box-shadow: 0 2px 8px rgba(234, 88, 12, 0.05);
        color: #292524 !important;
        font-size: 1.02rem;
        font-weight: 500;
    }

    .assistant-card {
        background: #ffffff;
        border: 1px solid #e7dfd3;
        border-left: 4px solid #c2410c;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(180, 140, 90, 0.06);
        color: #1c1917 !important;
        line-height: 1.75;
        font-size: 1.02rem;
    }

    .assistant-card table {
        width: 100%;
        border-collapse: collapse;
        margin: 12px 0 18px 0;
        background: #faf8f5;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #ede5d8;
    }

    .assistant-card th {
        background: #f3ece1;
        color: #78350f;
        font-weight: 700;
        padding: 10px 14px;
        text-align: left;
        border-bottom: 2px solid #e2d9cc;
        font-size: 0.95rem;
    }

    .assistant-card td {
        padding: 10px 14px;
        border-bottom: 1px solid #ede5d8;
        font-size: 0.95rem;
        color: #292524;
    }

    .assistant-card tr:last-child td {
        border-bottom: none;
    }

    /* 스킬 실행 배지 */
    .skill-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #ffedd5;
        color: #9a3412;
        border: 1px solid #fdba74;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 10px;
    }

    .stat-badge {
        background: #fef3c7;
        color: #92400e;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 0.88rem;
        border: 1px solid #fde68a;
    }

    .skill-chip {
        background: #ffffff;
        border: 1px solid #e2d9cc;
        border-radius: 10px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.86rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. 세션 상태 초기화
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "안녕하세요냥! 🐾 저는 고려대 도서관 학술 연구 및 120여 개 특화 멀티툴을 척척 실행해 드리는 **KU ScholarCat**이다냥! 🎓🐱✨\n\n"
                "🌟 **사용자의 관심사와 문맥을 깊이 분석하여 딱 맞는 핵심 논문과 자료를 스마트하게 큐레이션해 드린다냥!** 📚\n"
                "- **고려대 dCollection 석·박사 학위논문**: 교내 우수 학위논문 메타데이터 및 원문 뷰어 링크 실시간 추출\n"
                "- **글로벌 학술 저널(IEEE, Springer 등)**: Open Access 및 실제 원문 열람 링크 연동\n"
                "- **도서관 소장자료**: 단행본 소장 위치 및 대출 현황 조회\n\n"
                "상단의 **호랑이냥 삼총사(치즈·모찌·쿠로)**를 클릭하면 도서관 꿀팁과 K-Skill 소개를 보실 수 있다냥! 무엇이든 편하게 물어보세요냥! 골골~ 🐾"
            ),
            "skill_info": None
        }
    ]

if "visited" not in st.session_state:
    st.session_state.visited = True
    current_stats = load_app_stats()
    current_stats["visitors"] += 1
    save_app_stats(current_stats)

if "cat_enabled" not in st.session_state:
    st.session_state.cat_enabled = True

if "is_thinking" not in st.session_state:
    st.session_state.is_thinking = False

# -----------------------------------------------------------------------------
# 3. 사이드바 - 설정 및 K-Skill 레지스트리
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 🐾 KU ScholarCat 설정")

    # API 키는 .env에서 백그라운드 자동 로드 (UI 노출 생략)
    gemini_key_input = os.getenv("GEMINI_API_KEY", DEFAULT_GEMINI_API_KEY)

    selected_model = st.selectbox(
        "🧠 Gemini AI 모델 선택",
        options=[
            "gemini-3.6-flash",
            "gemini-flash-latest"
        ],
        index=0,
        format_func=lambda x: {
            "gemini-3.6-flash": "⚡ Gemini 3.6 Flash (초고속·무제한 토큰 추천)",
            "gemini-flash-latest": "🚀 Gemini Flash Latest (최신 릴리즈)"
        }.get(x, x),
        help="사용자님의 Google Gemini 계정으로 풍부한 쿼터와 초고속 응답을 제공합니다."
    )

    temperature = st.slider(
        "창의성 (Temperature)",
        min_value=0.0,
        max_value=1.0,
        value=0.15,
        step=0.05,
        help="낮을수록(0.1~0.2) 사실과 공공데이터에 엄격하게 답변하고, 높을수록 표현이 다양해집니다."
    )
    
    top_k = st.slider(
        "참조 스킬 개수 (Top-K)",
        min_value=1,
        max_value=6,
        value=4,
        help="사용자 질문 분석 시 K-Skill 중 연관도가 가장 높은 상위 N개의 도구를 후보로 탐색합니다. (기본 4개 권장)"
    )

    # 엔진 인스턴스 캐싱 (페이지 리런 시 재초기화 방지로 극적인 속도 향상)
    @st.cache_resource(show_spinner=False)
    def get_cached_engine(key: str):
        return CatRAGEngine(gemini_api_key=key)

    engine = get_cached_engine(gemini_key_input)
    st.session_state.rag_engine = engine

    st.markdown("---")

    # 인터랙티브 고양이 컨트롤
    st.markdown("### 🐱 산책하는 고양이 삼총사")
    col_c_toggle, col_c_num = st.columns([1.2, 1])
    with col_c_toggle:
        cat_toggle = st.checkbox("고양이 켜기", value=st.session_state.cat_enabled)
    with col_c_num:
        cat_num = st.selectbox("마리 수", options=[1, 2, 3], index=2)

    if cat_toggle != st.session_state.cat_enabled:
        st.session_state.cat_enabled = cat_toggle
        st.rerun()

    if "churu_feed_trigger" not in st.session_state:
        st.session_state.churu_feed_trigger = 0

    if st.button("🐟 고양이에게 츄르주기", use_container_width=True):
        st.session_state.churu_feed_trigger += 1
        st.toast("치즈, 모찌, 쿠로에게 츄르를 5개씩 가득 주었다냥! 💖 배부르고 기운차다냥~ 😻", icon="🐟")
        st.rerun()

    st.markdown("---")

    # K-Skill 지식 레지스트리 현황
    st.markdown("### 📚 K-Skill 레지스트리 현황")

    # 캐싱: ChromaDB 풀스캔 방지 (5분 TTL)
    @st.cache_data(ttl=300, show_spinner=False)
    def get_cached_doc_count():
        return engine.get_document_count()

    @st.cache_data(ttl=300, show_spinner=False)
    def get_cached_skills():
        return engine.get_indexed_skills()

    total_skills = get_cached_doc_count()
    st.markdown(f"색인된 한국 특화 도구: <span class='stat-badge'>⚡ {total_skills}개</span>", unsafe_allow_html=True)

    with st.expander("🛠️ 등록된 K-Skill 목록 보기", expanded=False):
        skills = get_cached_skills()
        if skills:
            for s in skills[:30]:  # 상위 30개 표시
                script_badge = "🐍 파이썬" if s["has_scripts"] else "📖 가이드"
                st.markdown(
                    f"<div class='skill-chip'><b>{s['skill_name']}</b> "
                    f"<span style='color:#c2410c; font-size:0.75rem;'>({script_badge})</span><br/>"
                    f"<span style='color:#78716c; font-size:0.78rem;'>{s['description'][:50]}...</span></div>",
                    unsafe_allow_html=True
                )
            if len(skills) > 30:
                st.caption(f"...외 {len(skills)-30}개 스킬 등록됨")
        else:
            st.caption("등록된 스킬 정보를 불러올 수 없습니다.")

    # 대화 관리 (대화 리셋 및 대화 저장)
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        if st.button("🗑️ 대화 리셋", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": (
                        "대화 기록이 초기화되었다냥! 🐾\n\n"
                        "고려대학교 dCollection 석박사 학위논문 및 도서관 교외접속(EzProxy) 원문 열람부터 K-Startup 창업공고, 주식 분석까지 무엇이든 다시 물어보세요냥! 골골~ 🐱✨"
                    ),
                    "skill_info": None
                }
            ]
            st.rerun()
    with col_c2:
        chat_text = "\n\n".join([f"[{m['role'].upper()}]: {m['content']}" for m in st.session_state.messages])
        st.download_button(
            "💾 저장",
            data=chat_text,
            file_name="solar_cat_chat_history.txt",
            mime="text/plain",
            use_container_width=True
        )

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # 실시간 방문자 수 및 누적 질문 수 집계 표시 (최하단, 30초 캐싱)
    @st.cache_data(ttl=30, show_spinner=False)
    def get_cached_stats():
        return load_app_stats()

    stats_data = get_cached_stats()
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.markdown(
            f"<div style='background:#ffffff; border:1px solid #e7dfd3; border-radius:12px; padding:10px 12px; text-align:center; box-shadow:0 2px 6px rgba(180,140,90,0.06);'>"
            f"<div style='font-size:0.75rem; color:#78716c; font-weight:600;'>👥 Visitor 수</div>"
            f"<div style='font-size:1.25rem; font-weight:800; color:#ea580c; margin-top:2px;'>{stats_data['visitors']:,}</div>"
            f"</div>",
            unsafe_allow_html=True
        )
    with col_stat2:
        st.markdown(
            f"<div style='background:#ffffff; border:1px solid #e7dfd3; border-radius:12px; padding:10px 12px; text-align:center; box-shadow:0 2px 6px rgba(180,140,90,0.06);'>"
            f"<div style='font-size:0.75rem; color:#78716c; font-weight:600;'>💬 질문 수</div>"
            f"<div style='font-size:1.25rem; font-weight:800; color:#c2410c; margin-top:2px;'>{stats_data['questions']:,}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

# -----------------------------------------------------------------------------
# 4. 인터랙티브 고양이 펫 위젯 렌더링
# -----------------------------------------------------------------------------
render_interactive_cat(
    is_active=st.session_state.cat_enabled,
    is_thinking=st.session_state.is_thinking,
    cat_count=cat_num,
    churu_feed_trigger=st.session_state.get("churu_feed_trigger", 0)
)

# -----------------------------------------------------------------------------
# 5. 메인 히어로 배너
# -----------------------------------------------------------------------------
st.markdown("""
<div class='hero-banner'>
    <div>
        <h1 class='hero-title'>🎓 KU ScholarCat</h1>
        <div class='hero-desc'>고려대학교 학술·논문 & 120+ 한국 특화 멀티툴 AI 어시스턴트</div>
    </div>
    <div class='cat-profile-badge'>
        <span class='cat-avatar'>🐾</span>
        <div>
            <div class='cat-badge-title'>KU ScholarCat 삼총사</div>
            <div class='cat-badge-sub'>● 고려대 학술 도서관 & K-Skill</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 6. 추천 퀵 질문 칩
# -----------------------------------------------------------------------------
st.markdown("<div style='font-size:0.92rem; font-weight:700; color:#78716c; margin-bottom:10px;'>💡 자주 묻는 질문 바로가기:</div>", unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)

suggested_prompt = None
with c1:
    if st.button("🎓 고려대 6G·NWDAF 학위논문", use_container_width=True):
        suggested_prompt = "고려대학교 dCollection에서 6G 및 NWDAF 관련 최신 석박사 학위논문 찾아줘냥!"
with c2:
    if st.button("🏛️ 반도체 HBM 논문 (EzProxy)", use_container_width=True):
        suggested_prompt = "최근 반도체 HBM 및 패키징 관련 최신 학술 논문과 고려대 도서관 EzProxy 원문 열람 링크를 알려줘냥!"
with c3:
    if st.button("🚀 이번 달 창업지원공고", use_container_width=True):
        suggested_prompt = "현재 모집 진행 중인 K-Startup 창업 지원사업 공고 3건을 찾아서 핵심 내용을 알려줘."
with c4:
    if st.button("📈 삼성전자 실시간 주가/수급", use_container_width=True):
        suggested_prompt = "삼성전자 현재 실시간 주가와 증권사 목표가, 최근 5일 외인/기관 수급 분석해줘."

# -----------------------------------------------------------------------------
# 7. 대화 메시지 렌더링
# -----------------------------------------------------------------------------
for msg in st.session_state.messages:
    if msg["role"] == "assistant":
        with st.chat_message("assistant", avatar="🐱"):
            # 스킬 실행 배지
            sinfo = msg.get("skill_info")
            if sinfo and sinfo.get("skill_detected"):
                badge_text = f"🛠️ 도구 호출: {sinfo['skill_detected']}"
                if sinfo.get("executed"):
                    badge_text += " (실시간 API 실행 완료 ✅)"
                st.markdown(f"<div class='skill-badge'>{badge_text}</div>", unsafe_allow_html=True)

            st.markdown(f"<div class='assistant-card'>{msg['content']}</div>", unsafe_allow_html=True)

            if sinfo and sinfo.get("executed") and sinfo.get("raw_output"):
                with st.expander(f"⚙️ K-Skill 실행 로그 및 원본 데이터 ({sinfo.get('command')})"):
                    st.code(sinfo.get("raw_output")[:2000], language="json")
    else:
        with st.chat_message("user", avatar="👤"):
            st.markdown(f"<div class='user-card'>{msg['content']}</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 8. 사용자 질의 입력 및 온디맨드 스킬 에이전트 실행
# -----------------------------------------------------------------------------
user_query = st.chat_input("고려대 논문(dCollection), 해외 저널(EzProxy), 또는 공공데이터를 질문하세요냥🐾 (예: 6G 학위논문 찾아줘)")

active_prompt = suggested_prompt if suggested_prompt else user_query

if active_prompt:
    increment_question_count()
    st.session_state.messages.append({"role": "user", "content": active_prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(f"<div class='user-card'>{active_prompt}</div>", unsafe_allow_html=True)

    with st.chat_message("assistant", avatar="🐱"):
        with st.spinner("K-Skill 카탈로그를 탐색하고 필요한 도구를 실행하고 있다냥...🐾"):
            try:
                st.session_state.is_thinking = True
                stream, source_skills, exec_info = engine.generate_response_stream(
                    active_prompt,
                    chat_history=st.session_state.messages[:-1],
                    k=top_k,
                    model_name=selected_model,
                    temperature=temperature
                )

                # 1단계 문맥 분석 및 K-Skill 도출 근거 배지 표시
                ctx_analysis = exec_info.get("context_analysis")
                if ctx_analysis and (ctx_analysis.get("user_interest_summary") or ctx_analysis.get("referenced_skill")):
                    ref_skill_label = f" | <b>연계 K-Skill</b>: <code>{ctx_analysis.get('referenced_skill')}</code>" if ctx_analysis.get("referenced_skill") else ""
                    st.markdown(
                        f"<div style='font-size:0.83rem; color:#78716c; background:#faf5ee; padding:6px 14px; border-radius:12px; margin-bottom:8px; border:1px solid #fed7aa;'>"
                        f"🎯 <b>1단계 문맥/스킬 분석</b>: {ctx_analysis.get('user_interest_summary', '')} "
                        f"| 핵심어: <code>{ctx_analysis.get('primary_keyword')}</code>"
                        f"{ref_skill_label}</div>",
                        unsafe_allow_html=True
                    )

                if exec_info.get("skill_detected"):
                    badge_text = f"🛠️ 도구 감지: {exec_info['skill_detected']}"
                    if exec_info.get("executed"):
                        badge_text += f" (2단계 크롤링 API 완료: {exec_info.get('command')}) ✅"
                    st.markdown(f"<div class='skill-badge'>{badge_text}</div>", unsafe_allow_html=True)

                response_container = st.empty()
                full_response = ""

                for chunk in stream:
                    full_response += chunk
                    response_container.markdown(
                        f"<div class='assistant-card'>{full_response} 🐾</div>",
                        unsafe_allow_html=True
                    )

                response_container.markdown(
                    f"<div class='assistant-card'>{full_response}</div>",
                    unsafe_allow_html=True
                )

                if exec_info.get("executed") and exec_info.get("raw_output"):
                    with st.expander(f"⚙️ K-Skill 실행 로그 및 원본 데이터 ({exec_info.get('command')})"):
                        st.code(exec_info.get("raw_output")[:2000], language="json")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response,
                    "skill_info": exec_info
                })
                st.session_state.is_thinking = False

            except Exception as e:
                st.session_state.is_thinking = False
                st.error(f"답변 생성 중 오류가 발생했습니다: {str(e)}")
