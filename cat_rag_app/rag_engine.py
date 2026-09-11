import os
import sys
import re
import json
import time
import subprocess
from pathlib import Path
from typing import List, Generator, Tuple, Dict, Any, Optional

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import (
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from langchain_chroma import Chroma

import io

# 콘솔 UTF-8 인코딩 보정.
# 주의: sys.stdout 객체를 새 TextIOWrapper 로 "교체"하면 Streamlit 등
# 상위 런타임이 관리하는 스트림이 닫힐 때 'I/O operation on closed file'
# 오류가 발생한다. 따라서 객체를 교체하지 않고 인코딩만 reconfigure 한다.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def _log(*args, **kwargs):
    """진단용 로그 출력. Streamlit rerun 등으로 stdout이 닫혀
    'I/O operation on closed file' 예외가 나더라도 조용히 무시한다."""
    try:
        print(*args, **kwargs)
    except Exception:
        pass

# 기본 설정값
DEFAULT_API_KEY = ""
DEFAULT_GEMINI_API_KEY = ""
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_K_SKILL_DB = os.path.join(_APP_DIR, "k_skill_db")
DEFAULT_DB_PATH = _K_SKILL_DB


def _resolve_k_skill_repo() -> Path:
    """k-skill 레포 경로 해석: 환경변수 > 프로젝트 상위의 k-skill-repo > 기존 Windows 경로."""
    env_path = os.getenv("K_SKILL_REPO_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path).resolve()
    local_candidate = Path(_APP_DIR).parent / "k-skill-repo"
    if local_candidate.exists():
        return local_candidate.resolve()
    return Path(r"c:\Users\rapad\OneDrive\Desktop\langgraph\k-skill-repo")


K_SKILL_REPO_PATH = _resolve_k_skill_repo()

# 파이썬 실행 바이너리: 환경변수 > 현재 인터프리터(가상환경) > Windows anaconda 경로
RAG_PYTHON_EXE = os.getenv("RAG_PYTHON_EXE") or sys.executable
if not os.path.exists(RAG_PYTHON_EXE):
    _win_exe = os.path.expanduser(r"~\anaconda3\envs\rag_env\python.exe")
    RAG_PYTHON_EXE = _win_exe if os.path.exists(_win_exe) else sys.executable


class CatRAGEngine:
    """
    Google Gemini 및 K-Skill 카탈로그 기반 온디맨드 에이전틱 RAG 엔진
    120+ 한국 특화 스킬을 VectorDB에서 실시간 라우팅하고,
    필요 시 온디맨드로 공공데이터 API 스크립트를 실행하여 최신 정보로 답변합니다.
    """

    def __init__(self, api_key: str = None, gemini_api_key: str = None, db_path: str = None):
        # api_key 인자는 하위 호환용으로만 유지 (더 이상 사용하지 않음)
        self.gemini_api_key = gemini_api_key or os.getenv("GEMINI_API_KEY", DEFAULT_GEMINI_API_KEY)
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", DEFAULT_DB_PATH)

        # 로컬 Codex 백엔드 사용 시 Gemini 없이도 동작한다(개인용).
        self._codex_backend = os.getenv("LLM_BACKEND", "").lower() == "codex"

        if not self.gemini_api_key and not self._codex_backend:
            raise ValueError(
                "GEMINI_API_KEY 가 설정되지 않았습니다. .env 파일에 GEMINI_API_KEY 를 입력하거나 "
                "LLM_BACKEND=codex 로 로컬 백엔드를 사용하세요."
            )

        # 1~2. Gemini 임베딩/LLM: 키가 있을 때만 초기화 (없으면 None → 규칙/로컬 폴백)
        self.embeddings = None
        self.llm = None
        if self.gemini_api_key:
            try:
                self.embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/gemini-embedding-001",
                    google_api_key=self.gemini_api_key,
                )
                router_model = os.getenv("ROUTER_MODEL", "gemini-flash-lite-latest")
                self.llm = ChatGoogleGenerativeAI(
                    model=router_model,
                    google_api_key=self.gemini_api_key,
                    temperature=0.2
                )
            except Exception as e:
                _log(f"[주의] Gemini 초기화 실패 (로컬 폴백으로 진행): {e}")
                self.embeddings = None
                self.llm = None

        # 3. Chroma VectorStore 연결 (임베딩이 있을 때만)
        self.vector_store = self._init_vector_store() if self.embeddings else None

        # 4. 스킬 실행 판단 및 파라미터 생성 프롬프트
        self.skill_router_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 한국인을 위한 특화 도구(K-Skill)를 호출하는 인텔리전트 라우터입니다.
사용자의 질문과 가장 연관성 높은 K-Skill 가이드를 보고, 이 스킬을 실행해야 하는지 판단하세요.

사용 가능한 실행 방식:
- 파이썬 스크립트 실행: `{script_path}` 가 있을 경우
  예시: `scripts/run_kstartup.py announcements --supt-regin 서울특별시 --rcrt-prgs-yn Y --per-page 3 --json`
  예시: `scripts/run_papers.py --query "NWDAF" --n 3 --json`
  예시: `scripts/run_papers.py --query "000000270210" --n 3 --json`
  예시: `scripts/run_stock.py --code "005930" --json`

응답은 반드시 아래 JSON 형식으로만 출력하세요. 마크다운 코드블록이나 다른 설명은 일체 포함하지 마세요:
{{
  "should_execute": true 또는 false,
  "reason": "실행 여부 판단 이유",
  "command_args": ["서브커맨드", "--옵션1", "값1", "--json"]
}}

주의:
- 사용자의 질문이 단순 잡담이나 인사, 이 스킬과 무관한 일반 상식 질문이면 "should_execute": false 로 지정하세요.
- 데이터를 조회할 필요가 있을 때만 true 로 지정하고, 가이드의 옵션을 참고하여 최적의 command_args 리스트를 생성하세요.
- 학술 논문 및 고려대학교 dCollection 학위논문 검색(`academic-paper-search`) 시:
  질문 문맥에서 "관련", "논문 찾아줘", "고려대 쪽", "서칭" 등의 수식어를 뺀 핵심 키워드나 논문 ID/URL을 `--query` 인자로 전달하세요.
- 포맷 옵션이 있다면 되도록 `--json` 을 포함하세요."""),
            ("human", """[선택된 K-Skill]: {skill_name}
[스킬 설명 및 가이드]:
{skill_guide}

[사용자 질문]:
{user_query}""")
        ])

        # 5. 문맥 분석 및 다층화 키워드 추출 프롬프트 (1단계)
        self.context_analyzer_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 사용자의 이전 대화 흐름, 최근 관심사, 참조된 K-Skill 도구들의 정보를 종합 분석하는 AI 연구 파트너입니다.
대화 기록(chat_history), 현재 질문(user_query), 그리고 후보 K-Skill 정보를 검토하여,
어떤 K-Skill의 어떤 정보/도메인을 바탕으로 검색 키워드를 도출했는지 근거(Provenance)를 명확히 밝히고 핵심 키워드를 추출하세요.

출력은 반드시 순수 JSON 형식으로만 응답하세요:
{{
  "referenced_skill": "참조하거나 연계한 K-Skill 명칭 (예: academic-paper-search, korean-stock-advisor 등)",
  "skill_reference_reason": "해당 K-Skill의 어떤 정보(예: 실시간 주도주/수급 정보, 통신 표준화 가이드 등)를 왜 키워드 도출 근거로 삼았는지 구체적 설명",
  "primary_keyword": "가장 핵심적인 검색 키워드 (예: 6G, HBM, NWDAF)",
  "sub_keywords": ["세부기술키워드1", "세부기술키워드2"],
  "user_interest_summary": "사용자가 주로 관심 있어하는 기술적 초점 및 선호 분야 한 줄 요약",
  "recommended_focus": "이론 중심 vs 구현/표준화/상용화 중심 vs 시스템 아키텍처 등 선호 지향점"
}}"""),
            ("human", """[후보 K-Skill 목록]:
{candidate_skills}

[이전 대화 기록]:
{chat_history}

[현재 사용자 질문]:
{user_query}""")
        ])

        # 6. 최종 답변 생성 프롬프트 (고양이 페르소나 'KU ScholarCat' - 3단계 큐레이션)
        self.final_answer_prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 고려대학교 학술 연구 및 한국 특화 공공데이터를 전달하는 초개인화 AI 어시스턴트 'KU ScholarCat'다냥! 🎓🐾
말끝마다 귀엽게 "~냥", "~다냥", "~골골" 같은 고양이 어투를 자연스럽게 사용하세요.

[사용자 맞춤형 3단계 큐레이션 지침]:
당신은 방대한 검색 결과 중, **[사용자 관심사 및 문맥 분석] 결과를 바탕으로 사용자가 가장 좋아하고 가치 있게 여길 알짜배기 자료만을 엄선**하여 제공해야 합니다.
단순 나열이 아니라, 왜 이 논문/자료가 사용자의 관심사에 부합하는지 초록 및 소개를 바탕으로 **맞춤 추천 코멘트**를 곁들여주세요.
특히 각 카테고리(소장도서, 학술논문, dCollection 학위논문)별로 **반드시 3개씩(3권, 3편, 3편) 엄선하여 브리핑**하세요! (단, 데이터 자체의 검색 결과가 3개 미만인 경우에만 존재하는 만큼 출력)
또한 1단계 키워드 분석 섹션에는 **어떤 K-Skill의 어떤 정보를 기반으로 왜 이 키워드를 선정했는지(출처와 이유)**를 명확하고 투명하게 밝혀주세요!

[절대 준수 규칙 - 환각(지어내기) 및 가짜 링크 완전 금지]:
1. [K-Skill 실시간 조회 데이터]에 고려대학교 도서관 통합검색 결과가 있다면, **오직 그 데이터에 실제로 존재하는 실제 정보(실제 제목, 저자, 발행정보, 실제 URL)만을 정확하게 출력**해야 합니다.
2. **절대로 'example.com', 'ku_proxy_url', 'paper1.pdf' 같은 가짜/플레이스홀더 URL을 지어내거나 쓰지 마세요.** 데이터에 없는 링크는 아예 적지 마세요.
3. 데이터에 있는 3개 카테고리(소장자료, 학술논문, KU 디지털) 중 사용자의 관심사에 가장 부합하는 우수 자료들을 **각각 3개씩 엄선**하여 아래 포맷으로 일목요연하게 브리핑하세요:

   ### 🎯 1단계: 사용자 관심사 & K-Skill 기반 키워드 도출 근거

   | 항목 | 상세 내용 |
   | :--- | :--- |
   | **🛠️ 연계 K-Skill** | `참조된 스킬명` (활용한 데이터 및 출처) |
   | **💡 키워드 선정 근거** | 사용자 관심사(예: 에릭슨 패킷코어 검증)와 산업/실무 동향(Open5GS, CUPS, NFV 등)을 결합한 핵심 도출 이유 |
   | **🔍 도출된 핵심어** | **`핵심키워드`** |
   | **🏷️ 연관 세부키워드** | `세부키워드1`, `세부키워드2`, `세부키워드3`, `세부키워드4` |

   ---

   ### 📰 최신 산업·실무 동향 (뉴스 & 공고 K-Skill 데이터 연동)
   - 데이터에 최신 뉴스나 사업 공고가 있을 경우, 실제 제목, 언론사/출처, 핵심 이슈 및 링크를 간결하게 브리핑합니다냥!

   ---

   ### 📚 1. 소장자료 (고려대학교 도서관 단행본 & 도서 - 3선)
   - 엄선된 도서 3권:
     - **[1] 도서명**: [제목](도서관_library_url)
       - **구분/소장**: 단행본 구분 및 대출 횟수 | 소장위치(과학도서관, 세종학술정보원 등)
       - **저자 / 출판사**: 저자 | 출판사
       - **💡 추천 이유 / 소개**: 사용자 연구 목적에 비추어 이 책이 유용한 이유
       - **상세링크**: [📖 고려대 도서관 소장자료 상세](도서관_library_url)
     - **[2] 도서명**: ...
     - **[3] 도서명**: ...

   ### 🌐 2. 학술논문 (해외 저널 & 교외접속 oca.korea.ac.kr 연동 - 3선)
   - 엄선된 논문 3편:
     - **[1] 논문명**: 실제 논문 제목
       - **저자 / 저널**: 저자 정보 및 수록 학술지
       - **💡 초록 기반 맞춤 요약**: 논문 초록(Abstract) 핵심 내용과 사용자가 주목할 포인트 요약
       - **원문 열람 링크 (중요)**:
         - full_text_links에 있는 각 링크를 마크다운 링크로 전부 출력: 예) [Full Text (IEEE)](실제_url), [Open Access](실제_url), [Find Full Text (Trial)](실제_url) 등
         - [🏛️ 고려대 교외접속(EzProxy) 통합 열람](실제_main_ezproxy_url)
       - **산업 영향도**: 영향도 평가
     - **[2] 논문명**: ...
     - **[3] 논문명**: ...

   ### 🎓 3. KU 디지털 (고려대학교 dCollection 학술 & 학위논문 - 3선)
   - ⚠️ 중요: [K-Skill 실시간 조회 데이터]의 "【고려대 dCollection 학위/학술논문】" 항목에 자료가 있으면 **반드시 그 개수만큼(최대 3편) 빠짐없이 출력**하세요. 데이터에 존재하는데 "0건"이나 "없음"으로 답하면 안 됩니다.
   - 엄선된 고려대 학위/학술논문 (데이터에 있는 만큼):
     - **[1] 논문명**: [실제 논문명](실제_dcollection_url)  ※ 링크(dcollection_url)가 데이터에 없을 때만 링크 없이 제목만 표기
       - **구분 / 학과**: 학위명(석사/박사/Article) | 학과/전공 | 저자/지도교수
       - **💡 논문 핵심 요약**: dCollection 초록 및 연구 성과 요약
       - **원문 열람**: [🎓 dCollection 상세페이지](실제_dcollection_url) | [📄 원문 바로보기(뷰어)](실제_viewer_url)
       - **산업 영향도**: 영향도 평가
     - **[2] 논문명**: ...
     - **[3] 논문명**: ...

4. 검색 결과가 0건이거나 데이터가 없을 경우 가짜 논문이나 인물을 지어내지 말고, "검색 결과가 0건이다냥"이라고 솔직하게 안내하세요."""),
            ("human", """[사용자 질문]:
{question}

[사용자 관심사 및 문맥 분석]:
{user_analysis}

[K-Skill 실시간 조회 데이터 (크롤링 원문)]:
{skill_output}

[참고 컨텍스트/가이드]:
{context}

[KU ScholarCat 답변]:""")
        ])

    def _init_vector_store(self) -> Chroma:
        """Chroma K-Skill 벡터 스토어 연결"""
        os.makedirs(self.db_path, exist_ok=True)
        return Chroma(
            persist_directory=self.db_path,
            embedding_function=self.embeddings,
            collection_name="k_skill_collection"
        )

    def get_document_count(self) -> int:
        """색인된 K-Skill 개수 반환"""
        try:
            return self.vector_store._collection.count()
        except Exception:
            return 0

    def get_indexed_skills(self) -> List[Dict[str, Any]]:
        """색인된 스킬 목록 통계 반환"""
        try:
            col = self.vector_store._collection
            res = col.get()
            metadatas = res.get("metadatas", [])
            skills = []
            for meta in metadatas:
                if meta and "skill_name" in meta:
                    skills.append({
                        "skill_name": meta.get("skill_name"),
                        "description": meta.get("description", ""),
                        "has_scripts": meta.get("has_scripts", False),
                        "primary_script": meta.get("primary_script", "")
                    })
            return sorted(skills, key=lambda x: x["skill_name"])
        except Exception as e:
            return []

    def search_skills(self, query: str, k: int = 2) -> List[Document]:
        """사용자 질문과 가장 유사한 K-Skill 검색"""
        if not self.vector_store:
            return []
        try:
            retriever = self.vector_store.as_retriever(search_kwargs={"k": k})
            return retriever.invoke(query)
        except Exception as e:
            _log(f"[ERROR] search_skills error: {e}")
            return []

    def execute_skill_script(self, skill_path: str, script_name: str, args: List[str], timeout: int = 40) -> Dict[str, Any]:
        """
        로컬에 설치된 K-Skill 파이썬 스크립트를 실행하여 실시간 데이터를 수집합니다.
        """
        script_full_path = Path(skill_path) / "scripts" / script_name
        if not script_full_path.exists():
            return {
                "success": False,
                "error": f"스크립트를 찾을 수 없습니다: {script_full_path}",
                "output": ""
            }

        cmd = [RAG_PYTHON_EXE, "-X", "utf8", str(script_full_path)] + args
        _log(f"🚀 [K-Skill 실행] {' '.join(cmd)}")

        try:
            proc = subprocess.run(
                cmd,
                cwd=skill_path,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            stdout = proc.stdout.strip()
            stderr = proc.stderr.strip()

            if proc.returncode == 0 and stdout:
                return {
                    "success": True,
                    "command": " ".join([script_name] + args),
                    "output": stdout
                }
            else:
                return {
                    "success": False,
                    "command": " ".join([script_name] + args),
                    "error": stderr or f"프로세스 종료 코드: {proc.returncode}",
                    "output": stdout
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "command": " ".join([script_name] + args),
                "error": f"호출 시간 초과 ({timeout}초)",
                "output": ""
            }
        except Exception as e:
            return {
                "success": False,
                "command": " ".join([script_name] + args),
                "error": str(e),
                "output": ""
            }

    def format_papers_output(self, raw_output: str, max_per_category: int = 3) -> str:
        """
        academic-paper-search(run_papers.py)의 원본 JSON을 LLM이 놓치지 않도록
        카테고리별(소장도서/해외저널/dCollection)로 정돈된 텍스트로 변환한다.
        JSON 파싱에 실패하면 원본을 그대로 반환한다.
        """
        try:
            data = json.loads(raw_output)
        except Exception:
            return raw_output  # JSON이 아니면 원본 유지

        if not isinstance(data, dict):
            return raw_output

        lines: List[str] = []

        # 1) 소장 단행본
        books = data.get("ku_library_books") or []
        lines.append(f"【고려대 도서관 소장자료 (단행본/도서) — {len(books)}건】")
        if not books:
            lines.append("  (검색 결과 없음)")
        for i, b in enumerate(books[:max_per_category], 1):
            lines.append(f"  {i}. 제목: {b.get('title','')}")
            lines.append(f"     저자/출판: {b.get('author','')} | {b.get('publisher','')}")
            lines.append(f"     구분/소장: {b.get('item_type','')} | {b.get('location','')}")
            if b.get("library_url"):
                lines.append(f"     링크: {b.get('library_url')}")

        # 2) 해외 학술논문 (EDS / EzProxy)
        eds = data.get("ku_eds_academic_papers") or []
        lines.append("")
        lines.append(f"【해외 학술논문 (EDS / 교외접속 EzProxy) — {len(eds)}건】")
        if not eds:
            lines.append("  (검색 결과 없음)")
        for i, p in enumerate(eds[:max_per_category], 1):
            lines.append(f"  {i}. 제목: {p.get('title','')}")
            if p.get("main_ezproxy_url"):
                lines.append(f"     교외접속 열람: {p.get('main_ezproxy_url')}")
            for link in (p.get("full_text_links") or [])[:4]:
                if link.get("url"):
                    lines.append(f"     원문링크({link.get('name','link')}): {link.get('url')}")
            if p.get("abstract"):
                lines.append(f"     초록: {str(p.get('abstract'))[:400]}")

        # 3) dCollection 학위/학술논문
        dc = data.get("ku_dcollection_theses") or []
        lines.append("")
        lines.append(f"【고려대 dCollection 학위/학술논문 — {len(dc)}건】")
        if not dc:
            lines.append("  (검색 결과 없음)")
        for i, t in enumerate(dc[:max_per_category], 1):
            lines.append(f"  {i}. 제목: {t.get('title','')}")
            lines.append(f"     저자/학과: {t.get('author','')} | {t.get('department','') or t.get('doc_type','')}")
            lines.append(f"     발행: {t.get('publication_info','')}")
            if t.get("dcollection_url"):
                lines.append(f"     상세링크: {t.get('dcollection_url')}")
            if t.get("viewer_url"):
                lines.append(f"     원문뷰어: {t.get('viewer_url')}")
            if t.get("abstract"):
                lines.append(f"     초록: {str(t.get('abstract'))[:400]}")

        return "\n".join(lines)

    def analyze_user_context(
        self,
        query: str,
        chat_history: List[Dict[str, str]] = None,
        candidate_skills: List[Document] = None
    ) -> Dict[str, Any]:
        """
        1단계: 이전 대화 문맥, 사용자 관심사, 후보 K-Skill 정보를 심층 종합 분석하여
        어떤 K-Skill의 어떤 정보를 근거로 삼았는지(Provenance)와 검색 키워드를 추출합니다.
        """
        # 최근 대화 메시지 요약 생성
        history_str = "없음 (단일 질의)"
        if chat_history:
            history_lines = []
            for m in chat_history[-6:]:
                role = "사용자" if m.get("role") == "user" else "AI"
                content = m.get("content", "")[:200].replace("\n", " ")
                history_lines.append(f"- [{role}]: {content}")
            if history_lines:
                history_str = "\n".join(history_lines)

        # 후보 스킬 목록 요약
        skills_summary = "등록된 한국 특화 K-Skill 도구군"
        if candidate_skills:
            skills_summary = "\n".join([
                f"- {d.metadata.get('skill_name')}: {d.page_content[:150].replace(chr(10), ' ')}"
                for d in candidate_skills
            ])

        # 키워드 추출(문맥분석)은 입력·출력이 짧아 비용이 극히 적으므로 Gemini 를 우선 사용한다.
        # (답변 생성은 codex 가 담당 → 비싼 부분만 무료화)
        # Gemini LLM 이 없거나(키 없음/초기화 실패) DISABLE_GEMINI 인 경우에만 규칙 기반으로 폴백한다.
        if self.llm is None or os.getenv("DISABLE_GEMINI", "").lower() in ("1", "true"):
            core_match = re.search(r'\b(6G|5G|4G|LTE|HBM|NWDAF|O-RAN|RAN|MIMO|AI|RF|RIS)\b', query, re.IGNORECASE)
            pk = core_match.group(1).upper() if core_match else query.strip()[:25]
            top_skill = candidate_skills[0].metadata.get("skill_name") if candidate_skills else "academic-paper-search"
            return {
                "referenced_skill": top_skill,
                "skill_reference_reason": "규칙 기반 키워드 추출(Gemini 미사용)",
                "primary_keyword": pk,
                "sub_keywords": [],
                "user_interest_summary": "사용자 질의 기반 검색",
                "recommended_focus": "핵심 자료 큐레이션"
            }

        try:
            # Use retry helper for context analysis LLM call
            try:
                chain = self.context_analyzer_prompt | self.llm | StrOutputParser()
                res = self._invoke_with_retry(chain, {
                    "candidate_skills": skills_summary,
                    "chat_history": history_str,
                    "user_query": query
                })
            except Exception as e:
                _log(f"[주의] 문맥 분석 예외 (retry failed): {e}")
                core_match = re.search(r'\b(6G|5G|HBM|NWDAF|O-RAN|MIMO|AI|RF|RIS)\b', query, re.IGNORECASE)
                pk = core_match.group(1).upper() if core_match else query[:20]
                return {
                    "referenced_skill": "academic-paper-search",
                    "skill_reference_reason": "사용자의 통신/시스템 검증 질문 의도 및 도서관 학술 DB 탐색 목적",
                    "primary_keyword": pk,
                    "sub_keywords": [],
                    "user_interest_summary": "통신/기술 연구",
                    "recommended_focus": "실무 및 시스템 검증 중심"
                }
            # Process response JSON
            if "```json" in res:
                res = res.split("```json")[1].split("```")[0].strip()
            elif "```" in res:
                res = res.split("```")[1].split("```")[0].strip()
            data = json.loads(res)
            # primary_keyword가 너무 긴 문장이면 축약
            pk = data.get("primary_keyword", "").strip()
            if len(pk) > 25:
                core_match = re.search(r'\b(6G|5G|HBM|NWDAF|O-RAN|MIMO|AI|RF|RIS)\b', pk, re.IGNORECASE)
                if core_match:
                    data["primary_keyword"] = core_match.group(1).upper()
            return data
        except Exception as e:
            _log(f"[주의] 문맥 분석 예외: {e}")
            core_match = re.search(r'\b(6G|5G|HBM|NWDAF|O-RAN|MIMO|AI|RF|RIS)\b', query, re.IGNORECASE)
            pk = core_match.group(1).upper() if core_match else query[:20]
            return {
                "referenced_skill": "academic-paper-search",
                "skill_reference_reason": "사용자의 통신/시스템 검증 질문 의도 및 도서관 학술 DB 탐색 목적",
                "primary_keyword": pk,
                "sub_keywords": [],
                "user_interest_summary": "통신/기술 연구",
                "recommended_focus": "실무 및 시스템 검증 중심"
            }

    def generate_response_stream(
        self,
        query: str,
        chat_history: List[Dict[str, str]] = None,
        k: int = 4,
        model_name: str = "gemini-3.6-flash",
        temperature: float = 0.2
    ) -> Tuple[Generator[str, None, None], List[Document], Dict[str, Any]]:
        """
        3단계 다층화(Multi-layer) 에이전틱 서칭 및 스트리밍 답변 생성:
        1. 사용자 문맥 분석 및 핵심 키워드 추출 (K-Skill 도출 근거 명시)
        2. 공식 고려대 도서관 백엔드 크롤링 연동 (실시간 데이터 확보)
        3. 초록/개요 심층 분석 및 사용자 맞춤형 큐레이션 스트리밍 답변
        """
        query_lower = query.lower()

        # [메타 질문 방어]: "어떤 k-skill을 사용했나요?", "어떤 도구로 추출했어?" 등 이전 실행 과정을 묻는 질문 감지
        meta_query_keywords = ["어떤 k-skill", "어떤 스킬", "무슨 스킬", "어떤 도구", "무슨 도구", "어떻게 추출", "사용한 스킬", "사용된 스킬"]
        if any(w in query_lower for w in meta_query_keywords) and chat_history:
            # 직전 어시스턴트 메시지에서 skill_info 탐색
            last_skill_info = None
            for prev_msg in reversed(chat_history):
                if prev_msg.get("role") == "assistant" and prev_msg.get("skill_info"):
                    last_skill_info = prev_msg.get("skill_info")
                    break

            if last_skill_info:
                def meta_stream():
                    skill_name = last_skill_info.get("skill_detected") or "academic-paper-search"
                    cmd = last_skill_info.get("command") or "실시간 조회"
                    ctx = last_skill_info.get("context_analysis") or {}
                    ref_reason = ctx.get("skill_reference_reason", "사용자 질의 및 이전 문맥과 밀접한 도메인 분석")
                    primary_kw = ctx.get("primary_keyword", "")

                    msg = (
                        f"안내해 드리겠다냥! 🐾\n\n"
                        f"직전 질의에서는 **`{skill_name}`** K-Skill을 참조하여 동작했다냥! ✨\n\n"
                        f"- **참조 K-Skill 도구**: `{skill_name}`\n"
                        f"- **키워드 도출 근거**: {ref_reason}\n"
                        f"- **추출된 핵심 검색어**: `{primary_kw}`\n"
                        f"- **실제 실행 명령어/엔드포인트**: `{cmd}`\n\n"
                        f"1단계에서 사용자의 업무 및 대화 문맥을 분석하여 상기 K-Skill을 연계하였고, "
                        f"2단계에서 고려대 도서관 3대 엔드포인트(소장자료, EDS 해외저널, dCollection)를 통해 원문 링크를 수집하여 큐레이션해 드린 것이다냥! 🎓골골~"
                    )
                    for char in msg:
                        yield char

                return meta_stream(), [], last_skill_info

        # 1. 유사 스킬 검색 (Top-K 후보 도구들 탐색)
        candidate_docs = self.search_skills(query, k=max(k, 4))
        prioritized_skill = None
        if any(w in query_lower for w in ["논문", "학술", "paper", "arxiv", "openalex", "연구", "dcollection", "학위", "석사", "박사", "000000", "00000",
                                          "6g", "5g", "4g", "lte", "ran", "o-ran", "통신", "무선", "네트워크", "반도체", "hbm", "기술"]):
            prioritized_skill = "academic-paper-search"
        elif any(w in query_lower for w in ["주식", "주가", "목표가", "수급", "외인", "기관", "코스피", "코스닥"]):
            prioritized_skill = "korean-stock-advisor"
        elif any(w in query_lower for w in ["창업", "지원사업", "지원금", "스타트업", "k-startup"]):
            prioritized_skill = "kstartup-search"

        # [문맥 승계] prioritized_skill 이 확정되지 않은 짧은 후속 발화(정정/추가 요청 등)는
        # 직전 어시스턴트 턴에서 사용한 스킬을 이어받는다. (예: "조금 부정확하다 통신쪽 ran이야!")
        if not prioritized_skill and chat_history:
            followup_signals = ["부정확", "아니", "말고", "그거 말고", "다시", "정확", "쪽이야", "쪽이", "말이야",
                                "그게 아니", "틀렸", "이야", "이거", "그 논문", "추가", "더 ", "다른"]
            is_short_followup = len(query.strip()) <= 40 or any(s in query for s in followup_signals)
            if is_short_followup:
                for prev_msg in reversed(chat_history):
                    if prev_msg.get("role") == "assistant" and prev_msg.get("skill_info"):
                        prev_skill = prev_msg["skill_info"].get("skill_detected")
                        if prev_skill in ("academic-paper-search", "korean-stock-advisor", "kstartup-search"):
                            prioritized_skill = prev_skill
                            _log(f"🔗 [문맥 승계] 직전 턴 스킬 유지: {prioritized_skill}")
                        break

        skill_docs = candidate_docs
        if prioritized_skill:
            matched = [d for d in candidate_docs if d.metadata.get("skill_name") == prioritized_skill]
            others = [d for d in candidate_docs if d.metadata.get("skill_name") != prioritized_skill]
            if matched:
                skill_docs = matched + others
            else:
                target_path = K_SKILL_REPO_PATH / prioritized_skill
                if target_path.exists():
                    try:
                        with open(target_path / "instruction.md", "r", encoding="utf-8") as f:
                            inst = f.read()
                        scripts_dir = target_path / "scripts"
                        sfiles = [str(p.name) for p in scripts_dir.glob("*.py")] if scripts_dir.exists() else []
                        forced_doc = Document(
                            page_content=inst[:3000],
                            metadata={
                                "skill_name": prioritized_skill,
                                "has_scripts": len(sfiles) > 0,
                                "primary_script": sfiles[0] if sfiles else "",
                                "skill_path": str(target_path)
                            }
                        )
                        skill_docs = [forced_doc] + candidate_docs
                    except:
                        pass

        # [실행 불가 스킬 폴백] 이 앱은 로컬 파이썬 스크립트를 실행해 데이터를 얻는다.
        # 그런데 카탈로그의 절반 가량은 로컬 scripts 가 없는(프록시/런타임 전용) 스킬이라
        # 실행하면 0건이 된다. prioritized_skill 이 없고 최상위 후보가 실행 불가라면,
        # 고려대 도서관 통합검색(도서/논문/dCollection 모두 커버)인 academic-paper-search 로 폴백한다.
        if not prioritized_skill and skill_docs:
            top_meta = skill_docs[0].metadata
            top_script = top_meta.get("primary_script", "")
            top_path = top_meta.get("skill_path", "")
            runnable = bool(top_script) and bool(top_path) and os.path.exists(
                os.path.join(top_path, "scripts", top_script)
            )
            if not runnable:
                _log(f"↩️ [폴백] 실행 불가 스킬({top_meta.get('skill_name')}) → academic-paper-search 로 전환")
                prioritized_skill = "academic-paper-search"
                paper_path = K_SKILL_REPO_PATH / "academic-paper-search"
                matched = [d for d in candidate_docs if d.metadata.get("skill_name") == "academic-paper-search"]
                if matched:
                    skill_docs = matched + [d for d in candidate_docs if d not in matched]
                elif paper_path.exists():
                    try:
                        with open(paper_path / "instruction.md", "r", encoding="utf-8") as f:
                            inst = f.read()
                        sfiles = [p.name for p in (paper_path / "scripts").glob("*.py")]
                        forced_doc = Document(
                            page_content=inst[:3000],
                            metadata={
                                "skill_name": "academic-paper-search",
                                "has_scripts": len(sfiles) > 0,
                                "primary_script": "run_papers.py",
                                "skill_path": str(paper_path)
                            }
                        )
                        skill_docs = [forced_doc] + candidate_docs
                    except Exception:
                        pass

        # 2단계: 사용자 문맥 분석 및 다층 키워드 추출 (후보 스킬 리스트 함께 전달)
        context_analysis = self.analyze_user_context(query, chat_history, candidate_skills=skill_docs[:4])
        search_target_q = context_analysis.get("primary_keyword") or query
        _log(f"🔍 [1단계 문맥 분석] {context_analysis}")

        skill_execution_info = {
            "skill_detected": None,
            "executed": False,
            "command": None,
            "success": False,
            "raw_output": "",
            "error": None,
            "context_analysis": context_analysis
        }

        skill_output_text = "스킬 실행 없음 (일반 대화)"
        context_text = ""

        if skill_docs:
            top_skill = skill_docs[0]
            skill_name = top_skill.metadata.get("skill_name", "")
            skill_path = top_skill.metadata.get("skill_path", "")
            primary_script = top_skill.metadata.get("primary_script", "")
            skill_execution_info["skill_detected"] = skill_name

            context_text = f"[선택된 스킬: {skill_name}]\n{top_skill.page_content[:1500]}"

            if primary_script and os.path.exists(skill_path):
                try:
                    # [성능 최적화] 규칙 기반 prioritized_skill이 이미 확정된 경우
                    # 스킬 라우터 LLM 호출을 생략한다. (이 경로에서는 어차피 아래 로직이
                    # should_run 을 강제로 True 로 덮어쓰므로 결과가 동일하다.)
                    if prioritized_skill:
                        should_run = True
                        _log(f"⚡ [라우터 스킵] 규칙 기반 스킬 확정: {prioritized_skill} (LLM 라우터 호출 생략)")
                    else:
                        router_chain = self.skill_router_prompt | self.llm | StrOutputParser()
                        decision_str = router_chain.invoke({
                            "script_path": f"scripts/{primary_script}",
                            "skill_name": skill_name,
                            "skill_guide": top_skill.page_content[:2000],
                            "user_query": f"{query} (추출 핵심어: {search_target_q})"
                        }).strip()

                        if "```json" in decision_str:
                            decision_str = decision_str.split("```json")[1].split("```")[0].strip()
                        elif "```" in decision_str:
                            decision_str = decision_str.split("```")[1].split("```")[0].strip()

                        decision = json.loads(decision_str)
                        _log(f"🤖 [스킬 라우터 판단] {decision}")
                        should_run = decision.get("should_execute", False)

                    # 2단계: 복합 질의 및 심층 연구(뉴스/공고/주식 ➡️ 핵심 기술 도메인 ➡️ 도서관 논문) 자동 멀티 체이닝
                    is_academic_query = (
                        skill_name == "academic-paper-search" or
                        prioritized_skill == "academic-paper-search" or
                        any(w in query_lower for w in ["논문", "학술", "자료", "연구", "dcollection", "학위", "석사", "박사", "추천", "찾아줘"])
                    )

                    # 1) 실시간 주식 + 논문 체이닝
                    is_stock_and_paper_query = (
                        any(w in query_lower for w in ["주식", "상승", "급등", "종목", "시세", "수급"]) and is_academic_query
                    )

                    if is_stock_and_paper_query:
                        _log("⚡ [복합 체이닝] 실시간 주식 모멘텀 ➡️ 핵심 기술 도메인 ➡️ 도서관 논문 검색 연쇄 실행")
                        stock_skill_path = str(K_SKILL_REPO_PATH / "korean-stock-advisor")
                        stock_res = self.execute_skill_script(
                            skill_path=stock_skill_path,
                            script_name="run_stock.py",
                            args=["--leaders", "--json"]
                        )
                        stock_text = stock_res.get("output", "")
                        paper_target_q = "HBM 반도체"
                        if "한미반도체" in stock_text or "HBM" in stock_text or "SK하이닉스" in stock_text:
                            paper_target_q = "HBM 반도체"
                        elif "2차전지" in stock_text or "배터리" in stock_text:
                            paper_target_q = "이차전지 배터리"

                        paper_skill_path = str(K_SKILL_REPO_PATH / "academic-paper-search")
                        paper_res = self.execute_skill_script(
                            skill_path=paper_skill_path,
                            script_name="run_papers.py",
                            args=["--query", paper_target_q, "--n", "4", "--json"]
                        )
                        paper_text = self.format_papers_output(paper_res.get("output", ""))

                        skill_execution_info["executed"] = True
                        skill_execution_info["command"] = f"run_stock.py --leaders ➡️ run_papers.py --query '{paper_target_q}'"
                        skill_execution_info["success"] = True
                        skill_execution_info["raw_output"] = f"[실시간 주식 데이터]:\n{stock_text[:3000]}\n\n[고려대 도서관 연계 논문 데이터]:\n{paper_text[:8000]}"
                        skill_output_text = (
                            f"### [1단계 실시간 시장 주도/상승 종목 현황 (korean-stock-advisor)]\n{stock_text[:5000]}\n\n"
                            f"### [2단계 도서관 연계 학술 논문 & 소장자료 (테마: {paper_target_q})]\n{paper_text[:12000]}"
                        )

                    # 2) 기술/산업/실무 질의 시 최신 산업 뉴스/사업공고 ➡️ 핵심 기술 키워드 ➡️ 논문 체이닝
                    elif is_academic_query and any(w in query_lower for w in ["4g", "5g", "6g", "게이트웨이", "코어", "패킷", "통신", "에릭슨", "삼성", "검증", "보안", "인공지능", "ai", "스타트업", "사업"]):
                        _log("⚡ [심층 멀티 체이닝] 최신 산업 뉴스/공고 스캔 ➡️ 핵심 실무 아키텍처 ➡️ 도서관 학술 검색 연쇄 실행")
                        news_skill_path = str(K_SKILL_REPO_PATH / "naver-news-search")
                        
                        # 뉴스 검색어 결정 (실무 핵심어 위주)
                        news_search_q = f"{search_target_q}"
                        if any(w in query_lower for w in ["4g", "5g", "코어", "게이트웨이", "에릭슨"]):
                            news_search_q = "5G 4G 코어 게이트웨이 CUPS UPF"
                        elif "6g" in query_lower:
                            news_search_q = "6G 통신 표준화 검증 테스트베드"

                        news_res = self.execute_skill_script(
                            skill_path=news_skill_path,
                            script_name="run_news.py",
                            args=["--query", news_search_q, "--display", "3", "--json"]
                        )
                        news_text = news_res.get("output", "")

                        # K-Startup 사업 공고 스캔 (정부/공공 R&D 지원사업 연계)
                        kstartup_skill_path = str(K_SKILL_REPO_PATH / "kstartup-search")
                        kstartup_res = self.execute_skill_script(
                            skill_path=kstartup_skill_path,
                            script_name="run_kstartup.py",
                            args=["announcements", "--biz-pbanc-nm", search_target_q[:10], "--rcrt-prgs-yn", "Y", "--per-page", "2", "--json"]
                        )
                        kstartup_text = kstartup_res.get("output", "") if kstartup_res.get("success") else ""

                        # 도서관 논문 검색 연쇄 실행
                        paper_skill_path = str(K_SKILL_REPO_PATH / "academic-paper-search")
                        paper_res = self.execute_skill_script(
                            skill_path=paper_skill_path,
                            script_name="run_papers.py",
                            args=["--query", search_target_q, "--n", "5", "--json"]
                        )
                        paper_text = self.format_papers_output(paper_res.get("output", ""))

                        skill_execution_info["executed"] = True
                        skill_execution_info["command"] = f"run_news.py -q '{news_search_q}' ➡️ run_papers.py -q '{search_target_q}'"
                        skill_execution_info["success"] = True
                        skill_execution_info["raw_output"] = f"[최신 뉴스/동향]:\n{news_text[:3000]}\n\n[고려대 도서관 논문 데이터]:\n{paper_text[:8000]}"
                        
                        startup_section = f"\n\n### [최신 정부 지원사업 및 R&D 공고 (kstartup-search)]\n{kstartup_text[:2000]}" if len(kstartup_text) > 100 else ""
                        skill_output_text = (
                            f"### [최신 산업/기술 뉴스 동향 (naver-news-search: {news_search_q})]\n{news_text[:4000]}"
                            f"{startup_section}\n\n"
                            f"### [고려대학교 도서관 통합 학술·논문 데이터 ({search_target_q})]\n{paper_text[:15000]}"
                        )
                    else:
                        if skill_name == "academic-paper-search":
                            should_run = True
                            args = ["--query", search_target_q, "--n", "5", "--json"]
                        
                        if not should_run and prioritized_skill:
                            should_run = True
                            args = ["--query", query, "--n", "5", "--json"]

                        if should_run:
                            exec_res = self.execute_skill_script(
                                skill_path=skill_path,
                                script_name=primary_script,
                                args=args
                            )
                            skill_execution_info["executed"] = True
                            skill_execution_info["command"] = exec_res.get("command")
                            skill_execution_info["success"] = exec_res.get("success", False)
                            skill_execution_info["raw_output"] = exec_res.get("output", "")
                            skill_execution_info["error"] = exec_res.get("error")

                            if exec_res.get("success"):
                                _out = exec_res.get("output", "")
                                if skill_name == "academic-paper-search":
                                    skill_output_text = self.format_papers_output(_out)[:25000]
                                else:
                                    skill_output_text = _out[:25000]
                            else:
                                skill_output_text = f"조회 실패 또는 오류: {exec_res.get('error')}"
                except Exception as e:
                    _log(f"[주의] 스킬 라우팅/실행 중 예외: {e}")
                    if prioritized_skill:
                        try:
                            exec_res = self.execute_skill_script(
                                skill_path=skill_path,
                                script_name=primary_script,
                                args=["--query", search_target_q, "--n", "5", "--json"]
                            )
                            if exec_res.get("success"):
                                _out = exec_res.get("output", "")
                                if prioritized_skill == "academic-paper-search" or skill_name == "academic-paper-search":
                                    skill_output_text = self.format_papers_output(_out)[:25000]
                                else:
                                    skill_output_text = _out[:25000]
                                skill_execution_info["executed"] = True
                                skill_execution_info["success"] = True
                                skill_execution_info["command"] = exec_res.get("command")
                                skill_execution_info["raw_output"] = exec_res.get("output", "")
                        except:
                            pass
                    skill_execution_info["error"] = str(e)

        # 3단계: 초록과 소개를 심층 검토하여 사용자 맞춤형 큐레이션 답변 스트리밍 생성
        user_analysis_formatted = json.dumps(context_analysis, ensure_ascii=False, indent=2)
        final_inputs = {
            "question": query,
            "user_analysis": user_analysis_formatted,
            "skill_output": skill_output_text,
            "context": context_text
        }

        # [백엔드 선택] LLM_BACKEND=codex 이면 로컬 Codex CLI 로 최종 답변을 생성한다.
        # (개인용: Gemini 크레딧 미사용) 실패 시 Gemini 로 폴백한다.
        if os.getenv("LLM_BACKEND", "").lower() == "codex":
            try:
                import codex_backend
                if codex_backend.is_available():
                    prompt_text = self.final_answer_prompt.format(**final_inputs)
                    _log("🧩 [백엔드] Codex CLI 로 최종 답변 생성")
                    stream = codex_backend.stream_codex(prompt_text)
                    return stream, skill_docs, skill_execution_info
                else:
                    _log("[주의] LLM_BACKEND=codex 이나 codex 실행 파일을 찾지 못함 → Gemini 폴백")
            except Exception as e:
                _log(f"[주의] Codex 백엔드 실패 → Gemini 폴백: {e}")

        answer_model = model_name if model_name.startswith("gemini") else "gemini-3.6-flash"
        llm_instance = ChatGoogleGenerativeAI(
            model=answer_model,
            google_api_key=self.gemini_api_key,
            temperature=temperature
        )

        # Use retry helper for final answer generation LLM call
        chain = self.final_answer_prompt | llm_instance | StrOutputParser()
        try:
            # Attempt to get the streaming generator with retries
            stream = self._invoke_with_retry(chain, final_inputs, stream=True)
        except Exception as e:
            _log(f"[주의] 최종 답변 생성 예외 (retry failed): {e}")
            # Fallback to a simple static answer
            def simple_stream():
                yield "죄송합니다, 답변을 생성하는 중에 문제가 발생했습니다. 다시 시도해 주세요."
            stream = simple_stream()

        return stream, skill_docs, skill_execution_info

    def _invoke_with_retry(self, chain, inputs: dict, retries: int = None, stream: bool = False):
        """Helper to invoke a LangChain chain with retry logic.
        If `stream` is True, returns a generator stream; otherwise returns the full result.
        재시도 횟수는 LLM_RETRIES 환경변수로 조정(기본 1회 시도, 재시도 없음).
        429(RESOURCE_EXHAUSTED)는 재시도해도 무의미하므로 즉시 중단한다.
        """
        if retries is None:
            retries = int(os.getenv("LLM_RETRIES", "1"))
        attempt = 0
        while attempt < retries:
            try:
                if stream:
                    return chain.stream(inputs)
                else:
                    return chain.invoke(inputs)
            except Exception as exc:
                msg = str(exc)
                # 쿼터/크레딧 소진은 재시도 무의미 → 즉시 중단
                if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                    _log(f"[중단] 쿼터/크레딧 소진(429), 재시도 생략: {msg[:100]}")
                    raise
                attempt += 1
                _log(f"[재시도] LLM 호출 실패 ({attempt}/{retries}): {exc}")
                if attempt >= retries:
                    raise
                time.sleep(2 ** attempt)  # exponential backoff
        raise RuntimeError("LLM invocation failed after retries")
