"""
k_skill_indexer.py
NomaDamas/k-skill 저장소의 모든 스킬 메타데이터 및 가이드를 파싱하여
Google Generative AI 임베딩 기반 Chroma VectorDB에 완벽한 UTF-8 인코딩으로 인덱싱합니다.
"""

import os
import sys
import json
import time
import shutil
from pathlib import Path
from dotenv import load_dotenv

# UTF-8 강제 설정
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

APP_DIR = Path(__file__).parent.resolve()
load_dotenv(APP_DIR / ".env")

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TARGET_DB_PATH = APP_DIR / "k_skill_db"

# k-skill 레포 경로: 환경변수 > 프로젝트 상위의 k-skill-repo > 기존 하드코딩 경로 순
def _resolve_repo_path() -> Path:
    env_path = os.getenv("K_SKILL_REPO_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path).resolve()
    local_candidate = (APP_DIR.parent / "k-skill-repo")
    if local_candidate.exists():
        return local_candidate.resolve()
    return Path(r"c:\Users\rapad\OneDrive\Desktop\langgraph\k-skill-repo").resolve()

K_SKILL_REPO_PATH = _resolve_repo_path()

def parse_skill_directory(skill_dir: Path):
    """단일 스킬 디렉토리에서 메타데이터와 가이드 본문을 추출합니다."""
    skill_name = skill_dir.name
    
    # 1. skill.json 파싱
    skill_json_path = skill_dir / "skill.json"
    description = ""
    profiles = []
    if skill_json_path.exists():
        try:
            with open(skill_json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                description = data.get("description", "")
                profiles = data.get("profiles", [])
        except Exception as e:
            print(f"[{skill_name}] skill.json 파싱 오류: {e}")
            
    # 2. instruction.md 또는 SKILL.md 파싱
    instruction_text = ""
    instruction_path = skill_dir / "instruction.md"
    skill_md_path = skill_dir / "SKILL.md"
    
    if instruction_path.exists():
        try:
            with open(instruction_path, "r", encoding="utf-8") as f:
                instruction_text = f.read()
        except Exception as e:
            print(f"[{skill_name}] instruction.md 읽기 오류: {e}")
    elif skill_md_path.exists():
        try:
            with open(skill_md_path, "r", encoding="utf-8") as f:
                instruction_text = f.read()
        except Exception as e:
            print(f"[{skill_name}] SKILL.md 읽기 오류: {e}")
            
    if not description and not instruction_text:
        return None
        
    # 3. scripts 폴더 내 실행 가능한 파이썬 스크립트 탐색
    scripts_dir = skill_dir / "scripts"
    script_files = []
    if scripts_dir.exists() and scripts_dir.is_dir():
        script_files = [str(p.name) for p in scripts_dir.glob("*.py")]
        
    content = f"""# 한국인 특화 스킬: {skill_name}
설명: {description}
프로필/속성: {', '.join(profiles)}
내장 실행 스크립트: {', '.join(script_files) if script_files else '없음'}

## 상세 설명 및 가이드
{instruction_text[:3000]}
"""

    metadata = {
        "skill_name": str(skill_name),
        "description": str(description[:250]),
        "has_scripts": bool(len(script_files) > 0),
        "primary_script": str(script_files[0] if script_files else ""),
        "skill_path": str(skill_dir),
    }
    
    return Document(page_content=content, metadata=metadata)

def index_k_skills():
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY 가 설정되지 않았습니다.")
        sys.exit(1)
        
    if not K_SKILL_REPO_PATH.exists():
        print(f"[ERROR] k-skill 레포지토리 경로를 찾을 수 없습니다: {K_SKILL_REPO_PATH}")
        sys.exit(1)
        
    print(f"🔍 k-skill 디렉토리 탐색 중: {K_SKILL_REPO_PATH}")
    skill_dirs = [p for p in K_SKILL_REPO_PATH.iterdir() if p.is_dir() and not p.name.startswith(".")]
    
    docs = []
    skipped_no_script = []
    for sdir in skill_dirs:
        if sdir.name in ["docs", "examples", "infra", "packages", "python-packages", "scripts", ".changeset", ".claude-plugin", ".github"]:
            continue
        # 이 앱은 로컬 파이썬 스크립트를 실행해 데이터를 얻으므로,
        # 실행 가능한 scripts/*.py 가 없는(프록시/런타임 전용) 스킬은 인덱싱에서 제외한다.
        scripts_dir = sdir / "scripts"
        runnable_scripts = [p for p in scripts_dir.glob("*.py")
                            if not p.name.startswith("test_") and p.name != "__init__.py"] if scripts_dir.is_dir() else []
        if not runnable_scripts:
            skipped_no_script.append(sdir.name)
            continue
        doc = parse_skill_directory(sdir)
        if doc:
            docs.append(doc)

    print(f"✅ 실행 가능한 K-Skill {len(docs)}개 추출 (실행 스크립트 없어 제외: {len(skipped_no_script)}개)")
    
    # 신규 전용 k_skill_db 디렉토리 초기화
    if TARGET_DB_PATH.exists():
        print(f"🗑️ 기존 DB 디렉토리 삭제: {TARGET_DB_PATH}")
        shutil.rmtree(TARGET_DB_PATH, ignore_errors=True)
        
    print("🚀 Google 임베딩 모델(models/gemini-embedding-001)로 인덱싱 시작...")
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=GEMINI_API_KEY
    )

    # 무료 티어 rate-limit(429) 대응: 작은 배치 + 배치 간 지연 + 지수 백오프 재시도
    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "5"))
    batch_delay = float(os.getenv("EMBED_BATCH_DELAY", "2.0"))  # 초
    max_retries = 6

    # 빈 컬렉션을 먼저 생성한 뒤 배치 단위로 add
    vector_store = Chroma(
        embedding_function=embeddings,
        persist_directory=str(TARGET_DB_PATH),
        collection_name="k_skill_collection"
    )

    total = len(docs)
    for i in range(0, total, batch_size):
        batch = docs[i:i + batch_size]
        end = min(i + batch_size, total)
        attempt = 0
        while True:
            try:
                vector_store.add_documents(batch)
                print(f"  - 임베딩 완료 ({i + 1}~{end}/{total})")
                break
            except Exception as e:
                msg = str(e)
                is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg
                attempt += 1
                if is_rate_limit and attempt <= max_retries:
                    wait = min(60, batch_delay * (2 ** attempt))
                    print(f"  ⚠️ Rate limit(429). {wait:.0f}초 대기 후 재시도 ({attempt}/{max_retries})...")
                    time.sleep(wait)
                    continue
                print(f"  ❌ 배치 {i + 1}~{end} 임베딩 실패: {e}")
                raise
        # 다음 배치 전 지연으로 RPM 한도 준수
        if end < total:
            time.sleep(batch_delay)
            
    print(f"🎉 성공적으로 {len(docs)}개 K-Skill이 VectorDB({TARGET_DB_PATH})에 적재되었습니다!")

if __name__ == "__main__":
    index_k_skills()
