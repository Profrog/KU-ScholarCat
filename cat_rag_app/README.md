# 🐱 Solar Cat RAG 챗봇 서비스 (cat_rag_app)

Upstage의 최신 **Document Parse (HTML 서식/표 보존 파싱)** 와 **Solar Pro LLM**, 그리고 **Chroma Vector DB**를 기반으로 구축된 지능형 인터랙티브 RAG 챗봇 서비스입니다.

화면 하단을 사뿐사뿐 걸어다니는 귀여운 고양이 마스코트 **'솔라캣'**과 함께 문서를 탐색하고 대화를 나눌 수 있습니다! 🐾

---

## ✨ 핵심 기능

1. **📁 멀티 파일 일괄 업로드 (`accept_multiple_files=True`)**
   - 여러 개의 PDF, TXT, MD 문서를 한 번에 드래그 앤 드롭으로 업로드
   - 실시간 진행 상황(프로그레스 바 및 스테이터스) 표시 및 Chroma 벡터 DB 일괄 색인
2. **🐾 화면을 산책하는 인터랙티브 고양이 펫**
   - 화면 하단을 부드럽게 좌우로 산책하는 귀여운 순수 애니메이션 마스코트
   - 마우스 호버 시 멈춰 서서 유쾌한 말풍선 출력 ("골골송~", "무엇이든 물어보라냥!")
   - 마우스 클릭 시 펄쩍 뛰며 💖✨ 하트 파티클 반응
   - LLM 검색/답변 생성 중 '집중 분석 모드'로 자동 전환
   - 사이드바에서 냥이 켜기/끄기 토글 및 '츄르 주기' 인터랙션 지원
3. **⚡ 고성능 Upstage Solar RAG 파이프라인**
   - `UpstageDocumentParseLoader` (HTML 모드): 복잡한 표나 폰트 스타일, 서식을 보존하여 파싱
   - `solar-embedding-1-large`: 한국어 및 전문 문서에 최적화된 고차원 벡터 임베딩
   - `solar-pro` / `solar-mini`: 고성능 추론 및 빠른 속도 모델을 UI에서 실시간 선택 가능
   - 타이핑 효과의 스트리밍 답변 생성
4. **🔍 투명한 출처 및 근거 제시 (Source Citations)**
   - 각 답변마다 참조된 문서의 파일명, 청크 번호, 원문 조각을 카드 형태로 즉시 확인 가능
5. **📊 지식 베이스 관리 대시보드**
   - 현재 색인된 총 청크 수 및 파일별 색인 현황 실시간 모니터링
   - 기존 `lag/vector.db`의 88개 청크 지식 기본 연동
6. **💡 퀵 질문 칩 & 편의 기능**
   - 자주 묻는 질문 원클릭 전송
   - 대화 내역 TXT 파일로 다운로드 기능

---

## 🚀 빠른 실행 방법

### 방법 1. 원클릭 실행 (가장 간단)
`cat_rag_app` 폴더 내의 **`run.bat`** 파일을 더블 클릭합니다.
가상환경(`rag_env`)을 자동으로 탐지하여 웹 브라우저(`http://localhost:8501`)를 기동합니다.

### 방법 2. 콘솔에서 실행
PowerShell 또는 터미널에서 다음 명령어를 실행합니다:

```powershell
cd c:\Users\rapad\OneDrive\Desktop\langgraph\cat_rag_app
& "$env:USERPROFILE\anaconda3\envs\rag_env\python.exe" -m streamlit run app.py
```

---

## 📂 디렉토리 구조

```
cat_rag_app/
├── app.py              # Streamlit 메인 대화형 웹 인터페이스
├── rag_engine.py       # Upstage Solar & Chroma 멀티 파일 RAG 엔진
├── cat_widget.py       # 화면 하단 산책 인터랙티브 고양이 펫 위젯
├── run.bat             # 원클릭 실행기
├── .env                # Upstage API 키 및 DB 경로 설정
├── README.md           # 본 안내 문서
└── uploads/            # 사용자가 업로드한 문서가 보관되는 폴더
```
