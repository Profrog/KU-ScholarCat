# 🎓 KU ScholarCat (고려대 학술 연구 & K-Skill RAG 냥비서)

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/AI%20Engine-Google%20Gemini%20Flash-orange.svg)](https://aistudio.google.com/)
[![Streamlit](https://img.shields.io/badge/Frontend-Streamlit%20Interactive-red.svg)](https://streamlit.io/)
[![University](https://img.shields.io/badge/Affiliation-Korea%20University%20%F0%9F%90%AF-crimson.svg)](https://library.korea.ac.kr/)

고려대학교 도서관 포털 공식 통합검색(소장 단행본, EBSCO EDS 해외학술저널, dCollection 학위논문) 실시간 크롤링 연동 및 120여 개 한국 특화 공공데이터 K-Skill을 자율적으로 구동하는 지능형 AI 에이전트 **KU ScholarCat** 프로젝트입니다.

---

## 🐯 주요 핵심 기능

1. **🏛️ 고려대학교 도서관 실시간 크롤링 연동**:
   - **소장도서**: 과학도서관, 중앙도서관 등 캠퍼스별 소장 위치, 청구기호, 대출 가능 여부 즉시 조회
   - **EBSCO EDS**: 세계 유수 해외 학술 논문 및 IEEE/Springer 저널 검색
   - **dCollection**: 석·박사 학위논문 메타데이터 및 원문 링크 연동

2. **🧠 Google Gemini 3.6 Flash 기반 고성능 3단계 RAG 파이프라인**:
   - **1단계 (관심사 & 최신 뉴스 맥락 파악)**: 질문 의도를 정밀 분석하고 K-Skill(네이버 뉴스 등)을 통해 최신 실무/산업 동향 파악
   - **2단계 (학술 및 도서 연계 탐색)**: 맥락에 기반한 최적의 학술 키워드를 도출하여 고려대 도서관 3대 엔드포인트 크롤링
   - **3단계 (고려대 호랑이냥이의 맞춤형 큐레이션)**: 분석한 도서와 논문을 사용자 연구/실무 배경에 맞추어 맞춤 답변 생성

3. **🐾 인터랙티브 고려대 호랑이냥 삼총사 (Cat Playground)**:
   - 고려대 크림슨 색상 목줄과 뚜렷한 호랑이 등 줄무늬, 이마 王자 문양을 지닌 3마리의 냥비서가 화면 상단을 자유롭게 산책
   - 왼쪽/오른쪽 보행 방향에 맞춰 캐릭터만 정밀 반전되며, 대사 말풍선과 태그는 가독성 있게 정방향 유지
   - 클릭 시 별빛/하트 파티클 점프, 마우스 호버 시 실시간 대사 반응

4. **🛠️ 120+ 한국 특화 K-Skill 온디맨드 실행**:
   - 네이버 뉴스 검색, 창업진흥원(K-Startup) 사업공고 조회, 국내 주식 종목 및 시장 동향 분석 등

---

## 📂 프로젝트 구조

```text
langgraph/
├── 🐱 cat_rag_app/          # Solar Cat KU 메인 애플리케이션 및 RAG 엔진
│   ├── app.py               # 메인 웹 프론트엔드 (Streamlit UI)
│   ├── rag_engine.py        # Gemini 기반 3단계 다층 분석 RAG 엔진
│   ├── cat_widget.py        # 2D 인터랙티브 캔버스 산책 고양이 위젯
│   ├── k_skill_indexer.py   # K-Skill 카탈로그 임베딩 및 Chroma DB 색인 스크립트
│   └── .env                 # 환경 변수 (API Key, 도서관 설정 등 / Git 제외)
│
├── 🛠️ k-skill-repo/         # K-Skill 온디맨드 도구 저장소
│   ├── academic-paper-search/ # 고려대 도서관 3대 엔드포인트 크롤러 (run_papers.py)
│   ├── naver-news-search/    # 네이버 뉴스 검색 연동기 (run_news.py)
│   ├── kstartup-search/      # 창업진흥원 사업공고 실시간 조회 (run_kstartup.py)
│   └── korean-stock-advisor/ # 실시간 국내 시장 주도주 및 종목 분석 (run_stock.py)
│
├── 🚀 run_solar_cat.bat     # Windows 원클릭 실행 스크립트
├── .env.example             # 환경 변수 설정 템플릿
└── .gitignore               # 개인 키, DB, 캐시 보호 설정
```

---

## ⚡ 설치 및 실행 방법

### 1. 필수 요구사항
- Python 3.10 이상
- Google AI Studio API Key (무료 티어 지원)

### 2. 가상환경 세팅 및 패키지 설치
```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 필수 라이브러리 설치
pip install streamlit langchain-google-genai google-generativeai chromadb beautifulsoup4 requests python-dotenv
```

### 3. 환경 변수 설정
프로젝트 루트 또는 `cat_rag_app/` 폴더에 `.env` 파일을 생성하고 발급받은 Google AI API 키를 입력합니다.
```env
# .env
GEMINI_API_KEY=your_gemini_api_key_here
CHROMA_DB_PATH=./cat_rag_app/k_skill_db
```

### 4. 실행
```bash
# 윈도우 환경: 배치 파일 더블클릭
run_solar_cat.bat

# 또는 터미널 실행:
streamlit run cat_rag_app/app.py --server.port 8080
```
- 브라우저에서 `http://localhost:8080` 접속

---

## 🔒 보안 및 개인정보 보호
- 본 프로젝트는 `.gitignore` 설정을 통해 API Key, 고려대 포털 계정, 로컬 벡터 DB(`k_skill_db`), 백업 파일(`_backup_archive/`)이 원격 저장소에 노출되지 않도록 철저히 관리됩니다.
