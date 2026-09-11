import streamlit as st
import streamlit.components.v1 as components

def render_interactive_cat(is_active: bool = True, is_thinking: bool = False, cat_count: int = 3, churu_feed_trigger: int = 0):
    """
    화면을 2D 다방향으로 자유롭게 누비는 3마리의 개성 만점 인터랙티브 고양이 펫 위젯
    - 치즈, 모찌, 쿠로 3마리 출현
    - 츄르 카운트 (기본 5개): 클릭할 때마다 차감, 0개 소진 시 배고픔 모드 및 경고
    - 츄르 주기 버튼으로 모두에게 5개 즉시 충전
    """
    if not is_active:
        cleanup_html = """
        <script>
            try {
                const oldCats = window.parent.document.getElementById('solar-cats-playground');
                if (oldCats) oldCats.remove();
            } catch(e) {}
        </script>
        """
        components.html(cleanup_html, height=0, width=0)
        return

    thinking_state = "true" if is_thinking else "false"
    feed_trigger_val = str(churu_feed_trigger)

    # 캐싱: 동일 파라미터면 HTML 재생성 스킵
    @st.cache_data(show_spinner=False)
    def _build_cat_html(thinking_state, cat_count, feed_trigger_val):
        return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta charset="utf-8">
    <style>
        /* 고양이 플레이그라운드 컨테이너 */
        #solar-cats-playground {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: 999990;
            overflow: hidden;
        }}

        .cat-actor {{
            position: absolute;
            pointer-events: auto;
            user-select: none;
            cursor: pointer;
            transition: transform 0.1s ease-out;
            will-change: transform, left, top;
        }}

        .cat-bubble-3d {{
            position: absolute;
            bottom: 74px;
            left: 50%;
            transform: translateX(-50%);
            background: #ffffff;
            color: #1c1917;
            border: 2px solid #d97706;
            border-radius: 16px;
            padding: 7px 14px;
            font-size: 12.5px;
            font-weight: 700;
            white-space: nowrap;
            box-shadow: 0 6px 20px rgba(217, 119, 6, 0.22);
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease, transform 0.25s ease;
            font-family: 'Pretendard', sans-serif;
            z-index: 1000;
        }}

        .cat-bubble-3d::after {{
            content: '';
            position: absolute;
            bottom: -6px;
            left: 50%;
            transform: translateX(-50%);
            border-width: 6px 6px 0;
            border-style: solid;
            border-color: #d97706 transparent;
        }}

        .cat-actor:hover .cat-bubble-3d,
        .cat-bubble-3d.active {{
            opacity: 1;
            transform: translateX(-50%) translateY(-6px);
        }}

        .cat-svg-canvas {{
            width: 72px;
            height: 60px;
            filter: drop-shadow(0 6px 12px rgba(160, 110, 50, 0.22));
        }}

        @keyframes tailSway {{
            0%, 100% {{ transform: rotate(0deg); }}
            50% {{ transform: rotate(26deg); }}
        }}
        .tail-anim {{
            transform-origin: 22px 46px;
            animation: tailSway 1.5s ease-in-out infinite;
        }}

        @keyframes legWalkA {{
            0%, 100% {{ transform: rotate(-18deg); }}
            50% {{ transform: rotate(18deg); }}
        }}
        @keyframes legWalkB {{
            0%, 100% {{ transform: rotate(18deg); }}
            50% {{ transform: rotate(-18deg); }}
        }}
        .leg-anim-f {{
            transform-origin: 54px 52px;
            animation: legWalkA 0.5s linear infinite;
        }}
        .leg-anim-b {{
            transform-origin: 30px 52px;
            animation: legWalkB 0.5s linear infinite;
        }}

        @keyframes blinkEyeAnim {{
            0%, 92%, 100% {{ transform: scaleY(1); }}
            96% {{ transform: scaleY(0.1); }}
        }}
        .cat-eye {{
            transform-origin: center;
            animation: blinkEyeAnim 3.2s ease-in-out infinite;
        }}

        @keyframes catHop {{
            0% {{ transform: translateY(0); }}
            40% {{ transform: translateY(-30px); }}
            100% {{ transform: translateY(0); }}
        }}
        .cat-hop-action {{
            animation: catHop 0.4s ease-out;
        }}

        .sparkle-particle {{
            position: fixed;
            pointer-events: none;
            font-size: 20px;
            z-index: 1000000;
            animation: popParticle 0.85s ease-out forwards;
        }}
        @keyframes popParticle {{
            0% {{ opacity: 1; transform: translate(0, 0) scale(0.5); }}
            100% {{ opacity: 0; transform: translate(var(--dx), var(--dy)) scale(1.4); }}
        }}

        .thinking-tag {{
            position: absolute;
            top: -6px;
            right: 0;
            background: linear-gradient(135deg, #f59e0b, #ea580c);
            color: #fff;
            font-size: 9px;
            font-weight: 800;
            padding: 2px 7px;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(234, 88, 12, 0.4);
            animation: tagPulse 1s infinite alternate;
        }}
        @keyframes tagPulse {{
            from {{ transform: scale(1); }}
            to {{ transform: scale(1.1); }}
        }}
    </style>
    </head>
    <body>
    <script>
    (function() {{
        try {{
            const doc = window.parent.document;
            const isThinking = {thinking_state};
            const catCount = {cat_count};

            // 플레이그라운드 컨테이너 획득 또는 생성
            let playground = doc.getElementById('solar-cats-playground');
            if (!playground) {{
                playground = doc.createElement('div');
                playground.id = 'solar-cats-playground';
                doc.body.appendChild(playground);
            }}

            // 기존 잔류 고양이 DOM 및 인스턴스 초기화 (이전 캐시 완벽 제거)
            if (window.parent._catAgents && window.parent._catAgents.length > 0) {{
                window.parent._catAgents.forEach(a => {{
                    if (a && a.el) a.el.remove();
                }});
            }}
            window.parent._catAgents = [];
            playground.innerHTML = '';

            // 스타일 시트 주입
            if (!doc.getElementById('cats-multi-style')) {{
                const styleEl = doc.createElement('style');
                styleEl.id = 'cats-multi-style';
                styleEl.textContent = `
                    #solar-cats-playground {{
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100vw;
                        height: 100vh;
                        pointer-events: none;
                        z-index: 99999999;
                        overflow: hidden;
                    }}
                    .cat-actor {{
                        position: absolute;
                        pointer-events: auto;
                        user-select: none;
                        cursor: pointer;
                        will-change: transform, left, top;
                        filter: drop-shadow(0 4px 10px rgba(160, 110, 50, 0.2));
                        z-index: 99999999;
                    }}
                    .cat-bubble-3d {{
                        position: absolute;
                        bottom: 68px;
                        left: 50%;
                        transform: translateX(-50%);
                        background: #ffffff;
                        color: #1c1917;
                        border: 2px solid #d97706;
                        border-radius: 16px;
                        padding: 7px 14px;
                        font-size: 12px;
                        font-weight: 700;
                        white-space: nowrap;
                        box-shadow: 0 6px 20px rgba(217, 119, 6, 0.22);
                        opacity: 0;
                        pointer-events: none;
                        transition: opacity 0.25s ease, transform 0.25s ease;
                        font-family: 'Pretendard', sans-serif;
                        z-index: 100000000;
                    }}
                    .cat-bubble-3d::after {{
                        content: '';
                        position: absolute;
                        bottom: -6px;
                        left: 50%;
                        transform: translateX(-50%);
                        border-width: 6px 6px 0;
                        border-style: solid;
                        border-color: #d97706 transparent;
                    }}
                    .cat-actor:hover .cat-bubble-3d,
                    .cat-bubble-3d.active {{
                        opacity: 1;
                        transform: translateX(-50%) translateY(-6px);
                    }}
                    .cat-svg-canvas {{
                        width: 65px;
                        height: 54px;
                        display: block;
                        transform-origin: center center;
                    }}
                    @keyframes tailSway {{
                        0%, 100% {{ transform: rotate(0deg); }}
                        50% {{ transform: rotate(26deg); }}
                    }}
                    .tail-anim {{
                        transform-origin: 22px 46px;
                        animation: tailSway 1.5s ease-in-out infinite;
                    }}
                    @keyframes legWalkA {{
                        0%, 100% {{ transform: rotate(-18deg); }}
                        50% {{ transform: rotate(18deg); }}
                    }}
                    @keyframes legWalkB {{
                        0%, 100% {{ transform: rotate(18deg); }}
                        50% {{ transform: rotate(-18deg); }}
                    }}
                    .leg-anim-f {{
                        transform-origin: 54px 52px;
                        animation: legWalkA 0.45s linear infinite;
                    }}
                    .leg-anim-b {{
                        transform-origin: 30px 52px;
                        animation: legWalkB 0.45s linear infinite;
                    }}
                    @keyframes blinkEyeAnim {{
                        0%, 92%, 100% {{ transform: scaleY(1); }}
                        96% {{ transform: scaleY(0.1); }}
                    }}
                    .cat-eye {{
                        transform-origin: center;
                        animation: blinkEyeAnim 3.2s ease-in-out infinite;
                    }}
                    @keyframes catHopAnim {{
                        0% {{ transform: translateY(0); }}
                        40% {{ transform: translateY(-30px); }}
                        100% {{ transform: translateY(0); }}
                    }}
                    .cat-hop-action {{
                        animation: catHopAnim 0.4s ease-out;
                    }}
                    .sparkle-particle {{
                        position: fixed;
                        pointer-events: none;
                        font-size: 20px;
                        z-index: 1000000;
                        animation: popParticle 0.85s ease-out forwards;
                    }}
                    @keyframes popParticle {{
                        0% {{ opacity: 1; transform: translate(0, 0) scale(0.5); }}
                        100% {{ opacity: 0; transform: translate(var(--dx), var(--dy)) scale(1.4); }}
                    }}
                    .thinking-tag {{
                        position: absolute;
                        top: -6px;
                        right: 0;
                        background: linear-gradient(135deg, #f59e0b, #ea580c);
                        color: #fff;
                        font-size: 9px;
                        font-weight: 800;
                        padding: 2px 7px;
                        border-radius: 10px;
                        box-shadow: 0 2px 6px rgba(234, 88, 12, 0.4);
                    }}
                    .churu-badge {{
                        display: none !important;
                    }}
                    .cat-bubble-3d.hungry {{
                        border-color: #ef4444;
                        color: #b91c1c;
                        background: #fff5f5;
                        box-shadow: 0 6px 20px rgba(239, 68, 68, 0.28);
                    }}
                    .cat-bubble-3d.hungry::after {{
                        border-color: #ef4444 transparent;
                    }}
                `;
                doc.head.appendChild(styleEl);
            }}

            // 3마리 고려대 학술 호랑이냥이 메타데이터 정의 (KU ScholarCat: 치즈, 모찌, 쿠로)
            const catProfiles = [
                {{
                    name: "치즈",
                    bodyColor: "#f97316",
                    bellyColor: "#fef3c7",
                    earColor: "#c2410c",
                    innerEar: "#fecdd3",
                    bellColor: "#fbbf24",
                    stripeColor: "#7c2d12", // 호랑이 줄무늬
                    quote: "치즈: KU ScholarCat 출동! 고려대 도서관 꿀팁 물어왔다냥! 🐯🐾",
                    quotes: [
                        "치즈: 💡 [단행본 팁] 도서관 홈페이지 '소장도서' 검색으로 청구기호와 위치를 바로 확인할 수 있다냥!",
                        "치즈: 🛠️ [K-Skill: naver-news-search] '최근 5G 동향'처럼 질문하면 최신 실무 뉴스를 요약해준다냥! 📰",
                        "치즈: 💡 [학술 팁] 과학도서관과 중앙도서관 소장 위치를 비교해 가장 가까운 서가를 추천한다냥!",
                        "치즈: 🛠️ [K-Skill: kstartup-search] 정부 지원사업 및 창업진흥원 공고를 실시간 스크랩한다냥! 🚀",
                        "치즈: 💡 [RAG 팁] 질문창에 논문 제목이나 관심 기술 키워드를 적으면 3단계로 분석해준다냥! ⚡",
                        "치즈: 🐾 고려대 호랑이 기운으로 오늘도 열공 화이팅이다냥! (=^･ω･^=)"
                    ]
                }},
                {{
                    name: "모찌",
                    bodyColor: "#fef9c3",
                    bellyColor: "#ffffff",
                    earColor: "#d97706",
                    innerEar: "#fda4af",
                    bellColor: "#991b1b", // 크림슨 레드 방울
                    stripeColor: "#b45309", // 골드 스트라이프
                    quote: "모찌: 크림슨 방울 흔들며 학위논문 찾아왔다냥! 🎓✨",
                    quotes: [
                        "모찌: 💡 [dCollection 팁] 고려대 석·박사 학위논문 메타데이터와 원문 PDF 링크를 바로 연결한다냥! 📖",
                        "모찌: 🛠️ [K-Skill: korean-stock-advisor] 코스피/코스닥 시장 주도주와 실시간 수급을 브리핑한다냥! 📈",
                        "모찌: 💡 [검색 꿀팁] 찾고 싶은 연구 분야(예: 패킷코어, AI 에이전트)를 입력하면 연계 도서를 찾아준다냥!",
                        "모찌: 🛠️ [K-Skill: academic-paper-search] 고려대 EzProxy와 연동해 교외에서도 원문 열람 가능하다냥! 🏛️",
                        "모찌: 💡 [큐레이션 팁] 단순 검색이 아니라 사용자 배경에 맞춘 3단계 분석 보고서를 드린다냥! 🐾",
                        "모찌: 💖 골골골... 지칠 땐 저를 클릭해서 점프 파티클을 감상하라냥!"
                    ]
                }},
                {{
                    name: "쿠로",
                    bodyColor: "#1e293b",
                    bellyColor: "#f8fafc",
                    earColor: "#0f172a",
                    innerEar: "#94a3b8",
                    bellColor: "#10b981",
                    stripeColor: "#020617", // 다크 스트라이프
                    quote: "쿠로: 날카로운 호랑이 눈빛으로 해외 저널을 스캔한다냥! 🐯🎩",
                    quotes: [
                        "쿠로: 💡 [EBSCO EDS 팁] 세계 최대 학술 데이터베이스에서 IEEE, Springer 해외 저널을 검색한다냥! 🌐",
                        "쿠로: 🛠️ [K-Skill: seoul-weather-risk] 연구실 나갈 때 침수/돌풍 위험도를 미리 확인하라냥! ☔",
                        "쿠로: 💡 [인용 팁] 도서와 논문의 상세 서지 링크를 클릭해 바로 도서관 대출 예약이 가능하다냥! 📚",
                        "쿠로: 🛠️ [K-Skill: nts_business_registration] 산학협력 파트너사의 휴폐업 상태를 즉시 검증한다냥! 🏢",
                        "쿠로: 💡 [다층 RAG] 최신 뉴스 + 도서관 도서 + 학위논문을 종합 크로스 체크한다냥! ⚡",
                        "쿠로: 🎩 이마에 王자 새긴 호랑이 냥이 쿠로가 끝까지 보좌하겠다냥!"
                    ]
                }}
            ];

            // 렌더링된 고양이 인스턴스 관리
            if (!window.parent._catAgents) {{
                window.parent._catAgents = [];
            }}

            // 츄르 주기 버튼 트리거 감지 -> 모든 고양이 츄르 5개로 즉시 충전
            const currentTrigger = parseInt("{feed_trigger_val}", 10) || 0;
            if (typeof window.parent._lastChuruTrigger === 'undefined') {{
                window.parent._lastChuruTrigger = currentTrigger;
            }} else if (window.parent._lastChuruTrigger !== currentTrigger) {{
                window.parent._lastChuruTrigger = currentTrigger;
                // 모든 고양이 츄르 5개로 재충전 & 배고픔 해제
                window.parent._catAgents.forEach((agent, i) => {{
                    agent.churuCount = 5;
                    const badge = doc.getElementById('churu-badge-' + i);
                    if (badge) {{
                        badge.classList.remove('empty');
                        badge.innerHTML = '🐟 5';
                    }}
                    const bubble = doc.getElementById('cat-bubble-' + i);
                    if (bubble) {{
                        bubble.classList.remove('hungry');
                        bubble.textContent = agent.profile.name + ": 츄르 충전 완료! 배부르고 힘이 난다냥! 💖😻";
                        bubble.classList.add('active');
                        if (agent._bubbleTimer) clearTimeout(agent._bubbleTimer);
                        agent._bubbleTimer = setTimeout(() => {{
                            bubble.classList.remove('active');
                        }}, 3500);
                    }}
                }});
            }}

            // 배고픔 전용 대사 정의
            const hungryQuotes = [
                "배고프다냥... 츄르가 시급하다냥! 😿🐟",
                "꼬르륵... 츄르 카운트가 0이다냥! 츄르를 달라냥! 🥫",
                "기운이 하나도 없다냥... [고양이에게 츄르주기]를 눌러달라냥! 🐾"
            ];

            // 이미 존재하는 에이전트의 profile & quotes 즉시 갱신 (코드 수정 즉시 반영)
            window.parent._catAgents.forEach((agent, i) => {{
                const p = catProfiles[i % catProfiles.length];
                agent.profile = p;
                if (typeof agent.churuCount === 'undefined') {{
                    agent.churuCount = 5;
                }}
                const bubble = doc.getElementById('cat-bubble-' + i);
                if (bubble && !isThinking) {{
                    if (agent.churuCount <= 0) {{
                        bubble.classList.add('hungry');
                        bubble.textContent = p.name + ": " + hungryQuotes[i % hungryQuotes.length];
                    }} else {{
                        bubble.classList.remove('hungry');
                        bubble.textContent = p.quote;
                    }}
                }}
                const badge = doc.getElementById('churu-badge-' + i);
                if (badge) {{
                    badge.innerHTML = '🐟 ' + agent.churuCount;
                    if (agent.churuCount <= 0) {{
                        badge.classList.add('empty');
                    }} else {{
                        badge.classList.remove('empty');
                    }}
                }}
            }});

            // 기존 에이전트 수 조정
            while (window.parent._catAgents.length < catCount) {{
                const idx = window.parent._catAgents.length;
                const profile = catProfiles[idx % catProfiles.length];
                
                const catEl = doc.createElement('div');
                catEl.className = 'cat-actor';
                catEl.id = 'cat-agent-' + idx;
                
                catEl.innerHTML = `
                    <div class="cat-bubble-3d" id="cat-bubble-${{idx}}">
                        ${{isThinking ? "열공 분석 중이다냥! 📖🐾" : profile.quote}}
                    </div>
                    ${{isThinking ? '<div class="thinking-tag">⚡열공중</div>' : ''}}
                    <svg class="cat-svg-canvas" viewBox="0 0 100 80" xmlns="http://www.w3.org/2000/svg">
                        <!-- 꼬리 & 호랑이 꼬리 마디 줄무늬 -->
                        <path class="tail-anim" d="M 22 46 C 10 44, 2 28, 14 18 C 18 14, 22 20, 18 24 C 12 30, 18 40, 24 44 Z" fill="${{profile.bodyColor}}" />
                        <path class="tail-anim" d="M 12 32 Q 15 30 18 33" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="2.2" stroke-linecap="round" fill="none" opacity="0.9" />
                        <path class="tail-anim" d="M 16 23 Q 19 21 21 24" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="2.2" stroke-linecap="round" fill="none" opacity="0.9" />
                        <!-- 뒷다리 -->
                        <ellipse class="leg-anim-b" cx="30" cy="54" rx="5" ry="10" fill="${{profile.earColor}}" />
                        <!-- 몸통 -->
                        <ellipse cx="44" cy="42" rx="24" ry="18" fill="${{profile.bodyColor}}" />
                        <ellipse cx="46" cy="42" rx="20" ry="14" fill="${{profile.bellyColor}}" />
                        
                        <!-- 🐯 맹렬하고 선명한 고려대 호랑이 등/옆구리 줄무늬 3선 -->
                        <path d="M 32 25 C 34 32, 33 37, 36 41 C 34 37, 37 31, 35 25 Z" fill="${{profile.stripeColor || '#451a03'}}" opacity="0.95" />
                        <path d="M 42 24 C 44 32, 41 39, 45 44 C 43 38, 47 31, 45 24 Z" fill="${{profile.stripeColor || '#451a03'}}" opacity="0.95" />
                        <path d="M 52 26 C 53 32, 51 38, 54 42 C 52 37, 55 31, 54 26 Z" fill="${{profile.stripeColor || '#451a03'}}" opacity="0.95" />
                        
                        <!-- 앞다리 -->
                        <ellipse class="leg-anim-f" cx="54" cy="54" rx="5" ry="10" fill="${{profile.earColor}}" />
                        <!-- 귀 -->
                        <polygon points="60,22 68,6 74,20" fill="${{profile.earColor}}" />
                        <polygon points="63,20 68,10 72,19" fill="${{profile.innerEar}}" />
                        <polygon points="76,22 84,8 88,24" fill="${{profile.earColor}}" />
                        <polygon points="78,20 83,11 86,21" fill="${{profile.innerEar}}" />
                        <!-- 얼굴 -->
                        <circle cx="74" cy="28" r="16" fill="${{profile.bodyColor}}" />
                        <circle cx="74" cy="28" r="13" fill="${{profile.bellyColor}}" />
                        
                        <!-- 🐯 이마 호랑이 삼지창 무늬 (왕 王 자 문양 정밀화) -->
                        <path d="M 74 13 L 74 23" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="2" stroke-linecap="round" />
                        <path d="M 70 15 L 78 15" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="1.8" stroke-linecap="round" />
                        <path d="M 71 18 L 77 18" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="1.5" stroke-linecap="round" />
                        <path d="M 69 22 L 79 22" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="2.2" stroke-linecap="round" />
                        
                        <!-- 🐯 뺨 호랑이 수염 무늬 -->
                        <path d="M 63 34 L 67 33" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="1.6" stroke-linecap="round" opacity="0.85" />
                        <path d="M 85 34 L 81 33" stroke="${{profile.stripeColor || '#451a03'}}" stroke-width="1.6" stroke-linecap="round" opacity="0.85" />
                        
                        <!-- 눈 -->
                        <ellipse class="cat-eye" cx="70" cy="25" rx="2.5" ry="3" fill="#1c1917" />
                        <ellipse class="cat-eye" cx="78" cy="25" rx="2.5" ry="3" fill="#1c1917" />
                        <circle cx="71" cy="24" r="0.9" fill="#ffffff" />
                        <circle cx="79" cy="24" r="0.9" fill="#ffffff" />
                        <!-- 코/입 -->
                        <polygon points="74,30 72,28 76,28" fill="#ef4444" />
                        <path d="M 72 31 Q 74 33 76 31" stroke="${{profile.earColor}}" stroke-width="1.3" fill="none" />
                        <!-- 수염 -->
                        <line x1="62" y1="28" x2="53" y2="27" stroke="${{profile.earColor}}" stroke-width="1.2" />
                        <line x1="62" y1="31" x2="52" y2="33" stroke="${{profile.earColor}}" stroke-width="1.2" />
                        <line x1="86" y1="28" x2="95" y2="27" stroke="${{profile.earColor}}" stroke-width="1.2" />
                        <line x1="86" y1="31" x2="96" y2="33" stroke="${{profile.earColor}}" stroke-width="1.2" />
                        <!-- 🏛️ 고려대 크림슨 목줄 & 방울 -->
                        <path d="M 64 36 Q 72 42 78 37" stroke="#991b1b" stroke-width="2.8" fill="none" />
                        <ellipse cx="70" cy="40" rx="4.5" ry="4.5" fill="${{profile.bellColor}}" stroke="#a16207" stroke-width="0.8" />
                    </svg>
                `;

                playground.appendChild(catEl);

                // 고양이 객체 상태 초기화 (화면 상단에서 출발)
                const startY = 30 + (idx * 45);
                const startX = 60 + (idx * 160);

                const svgEl = catEl.querySelector('.cat-svg-canvas');

                const agent = {{
                    el: catEl,
                    svg: svgEl,
                    profile: profile,
                    churuCount: 5,
                    x: startX,
                    y: startY,
                    vx: (Math.random() * 1.6 + 0.8) * (Math.random() < 0.5 ? 1 : -1),
                    vy: (Math.random() * 1.2 + 0.4) * (Math.random() < 0.5 ? 1 : -1),
                    isHovered: false,
                    isPaused: false,
                    pauseTimer: 0
                }};

                // 호버 인터랙션
                catEl.addEventListener('mouseenter', () => {{
                    agent.isHovered = true;
                    const bubble = doc.getElementById('cat-bubble-' + idx);
                    if (bubble && !isThinking) {{
                        const curProfile = agent.profile || profile;
                        if (agent.churuCount <= 0) {{
                            bubble.classList.add('hungry');
                            bubble.textContent = curProfile.name + ": " + hungryQuotes[idx % hungryQuotes.length];
                        }} else {{
                            bubble.classList.remove('hungry');
                            const qs = curProfile.quotes;
                            bubble.textContent = qs[Math.floor(Math.random() * qs.length)];
                        }}
                    }}
                }});

                catEl.addEventListener('mouseleave', () => {{
                    agent.isHovered = false;
                }});

                // 클릭 점프 & 파티클 & 츄르 차감 / 배고픔 모드 판별
                catEl.addEventListener('click', () => {{
                    catEl.classList.add('cat-hop-action');
                    setTimeout(() => catEl.classList.remove('cat-hop-action'), 400);

                    const bubble = doc.getElementById('cat-bubble-' + idx);
                    const badge = doc.getElementById('churu-badge-' + idx);
                    const curProfile = agent.profile || profile;

                    // 츄르 차감 또는 배고픔 처리
                    if (agent.churuCount > 0) {{
                        agent.churuCount--;
                    }}

                    // 뱃지 업데이트
                    if (badge) {{
                        badge.innerHTML = '🐟 ' + agent.churuCount;
                        if (agent.churuCount <= 0) {{
                            badge.classList.add('empty');
                        }} else {{
                            badge.classList.remove('empty');
                        }}
                    }}

                    // 말풍선 대사 처리
                    if (bubble && !isThinking) {{
                        if (agent.churuCount <= 0) {{
                            // 츄르가 0이 되었거나 0인 상태: 배고프다는 대사만 출력 & 빨간색 스타일
                            bubble.classList.add('hungry');
                            bubble.textContent = curProfile.name + ": " + hungryQuotes[idx % hungryQuotes.length];
                        }} else {{
                            // 아직 츄르가 남아있을 때: 꿀팁 대사 교체
                            bubble.classList.remove('hungry');
                            const qs = curProfile.quotes;
                            bubble.textContent = qs[Math.floor(Math.random() * qs.length)];
                        }}
                        bubble.classList.add('active');
                        if (agent._bubbleTimer) clearTimeout(agent._bubbleTimer);
                        agent._bubbleTimer = setTimeout(() => {{
                            bubble.classList.remove('active');
                        }}, 4000);
                    }}

                    // 파티클 (츄르가 있을 땐 하트/생선, 배고플 땐 눈물/경고)
                    const particleIcons = agent.churuCount > 0 
                        ? ['💖', '🐾', '✨', '😻', '🐟', '🧶'] 
                        : ['😿', '💧', '🐟', '🥫', '⚠️'];
                    
                    for (let p = 0; p < 6; p++) {{
                        const pt = doc.createElement('div');
                        pt.className = 'sparkle-particle';
                        pt.textContent = particleIcons[p % particleIcons.length];
                        const rect = catEl.getBoundingClientRect();
                        pt.style.left = (rect.left + 35) + 'px';
                        pt.style.top = (rect.top + 10) + 'px';
                        const dx = (Math.random() - 0.5) * 80 + 'px';
                        const dy = -(Math.random() * 60 + 30) + 'px';
                        pt.style.setProperty('--dx', dx);
                        pt.style.setProperty('--dy', dy);
                        doc.body.appendChild(pt);
                        setTimeout(() => pt.remove(), 850);
                    }}
                }});

                window.parent._catAgents.push(agent);
            }}

            // 초과된 고양이 제거
            while (window.parent._catAgents.length > catCount) {{
                const agent = window.parent._catAgents.pop();
                if (agent && agent.el) agent.el.remove();
            }}

            // 2D 다방향 산책 루프 (상/하/좌/우/대각선 자유 유영)
            if (!window.parent._catMultiLoop) {{
                window.parent._catMultiLoop = setInterval(() => {{
                    const winW = window.parent.innerWidth;
                    const winH = window.parent.innerHeight;

                    // 이동 가능 범위 (화면 최상단 영역을 활발히 배회: 상단 15px ~ 240px)
                    const minX = 20;
                    const maxX = winW - 80;
                    const minY = 15;
                    const maxY = Math.min(240, Math.floor(winH * 0.38));

                    window.parent._catAgents.forEach((cat, i) => {{
                        if (cat.isHovered) return;

                        // 가끔 멈춰서 낮잠/그루밍
                        if (cat.isPaused) {{
                            cat.pauseTimer--;
                            if (cat.pauseTimer <= 0) {{
                                cat.isPaused = false;
                                // 쉴 때 방향 새로 전환
                                const angle = Math.random() * Math.PI * 2;
                                const speed = Math.random() * 1.4 + 0.8;
                                cat.vx = Math.cos(angle) * speed;
                                cat.vy = Math.sin(angle) * speed;
                            }}
                            return;
                        }}

                        // 위치 갱신
                        cat.x += cat.vx;
                        cat.y += cat.vy;

                        // 좌우 벽 충돌 감지 및 턴
                        if (cat.x >= maxX) {{
                            cat.x = maxX;
                            cat.vx = -Math.abs(cat.vx);
                        }} else if (cat.x <= minX) {{
                            cat.x = minX;
                            cat.vx = Math.abs(cat.vx);
                        }}

                        // 상하 벽 충돌 감지 및 턴
                        if (cat.y >= maxY) {{
                            cat.y = maxY;
                            cat.vy = -Math.abs(cat.vy);
                        }} else if (cat.y <= minY) {{
                            cat.y = minY;
                            cat.vy = Math.abs(cat.vy);
                        }}

                        // 랜덤 방향 미세 굴절 (자연스러운 산책)
                        if (Math.random() < 0.02) {{
                            cat.vx += (Math.random() - 0.5) * 0.5;
                            cat.vy += (Math.random() - 0.5) * 0.4;
                            // 속도 제한
                            cat.vx = Math.max(-2.0, Math.min(2.0, cat.vx));
                            cat.vy = Math.max(-1.4, Math.min(1.4, cat.vy));
                        }}

                        // 랜덤 정지 (가끔 쉬기)
                        if (Math.random() < 0.005) {{
                            cat.isPaused = true;
                            cat.pauseTimer = Math.floor(Math.random() * 70) + 40;
                        }}

                        // DOM 반영
                        cat.el.style.left = cat.x + 'px';
                        cat.el.style.top = cat.y + 'px';

                        // 이동 방향에 맞춰 고양이 본체(SVG)만 좌우 반전 및 미세 상하 틸트 (대사 말풍선은 뒤집히지 않음)
                        const flipX = cat.vx >= 0 ? 1 : -1;
                        const tilt = Math.max(-12, Math.min(12, cat.vy * 6));
                        const targetSvg = cat.svg || cat.el.querySelector('.cat-svg-canvas');
                        if (targetSvg) {{
                            targetSvg.style.transform = `scaleX(${{flipX}}) rotate(${{tilt * flipX}}deg)`;
                        }}
                        cat.el.style.transform = 'none';
                    }});
                }}, 35);
            }}

        }} catch (err) {{
            console.warn('Multi-cat playground error:', err);
        }}
    }})();
    </script>
    </body>
    </html>
    """

    html_code = _build_cat_html(thinking_state, cat_count, feed_trigger_val)
    components.html(html_code, height=0, width=0)
