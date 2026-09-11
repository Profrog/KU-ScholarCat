"""
k_skill_indexer.py
NomaDamas/k-skill 저장소의 모든 스킬 메타데이터 및 가이드를 파싱하여
Upstage 임베딩 기반 Chroma VectorDB에 완벽한 UTF-8 인코딩으로 인덱싱합니다.
"""

import os
import sys
import json
import shutil
from pathlib import Path
from dotenv import load_dotenv

# UTF-8 강제 설정
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

APP_DIR = Path(__file__).parent.resolve()
load_dotenv(APP_DIR / ".env")

from langchain_upstage import UpstageEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

UPSTAGE_API_KEY = os.getenv("UPSTAGE_API_KEY")
TARGET_DB_PATH = APP_DIR / "k_skill_db"
K_SKILL_REPO_PATH = Path(r"c:\Users\rapad\OneDrive\Desktop\langgraph\k-skill-repo").resolve()

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
    if not UPSTAGE_API_KEY:
        print("[ERROR] UPSTAGE_API_KEY 가 설정되지 않았습니다.")
        sys.exit(1)
        
    if not K_SKILL_REPO_PATH.exists():
        print(f"[ERROR] k-skill 레포지토리 경로를 찾을 수 없습니다: {K_SKILL_REPO_PATH}")
        sys.exit(1)
        
    print(f"🔍 k-skill 디렉토리 탐색 중: {K_SKILL_REPO_PATH}")
    skill_dirs = [p for p in K_SKILL_REPO_PATH.iterdir() if p.is_dir() and not p.name.startswith(".")]
    
    docs = []
    for sdir in skill_dirs:
        if sdir.name in ["docs", "examples", "infra", "packages", "python-packages", "scripts", ".changeset", ".claude-plugin", ".github"]:
            continue
        doc = parse_skill_directory(sdir)
        if doc:
            docs.append(doc)
            
    print(f"✅ 총 {len(docs)} 개의 K-Skill 문서를 추출하였습니다.")
    
    # 신규 전용 k_skill_db 디렉토리 초기화
    if TARGET_DB_PATH.exists():
        print(f"🗑️ 기존 DB 디렉토리 삭제: {TARGET_DB_PATH}")
        shutil.rmtree(TARGET_DB_PATH, ignore_errors=True)
        
    print("🚀 Upstage 임베딩 모델(solar-embedding-1-large)로 인덱싱 시작...")
    embeddings = UpstageEmbeddings(
        model="solar-embedding-1-large",
        upstage_api_key=UPSTAGE_API_KEY
    )
    
    batch_size = 25
    vector_store = None
    
    for i in range(0, len(docs), batch_size):
        batch = docs[i:i+batch_size]
        print(f"  - 임베딩 진행 중... ({i+1}~{min(i+batch_size, len(docs))}/{len(docs)})")
        if vector_store is None:
            vector_store = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                persist_directory=str(TARGET_DB_PATH),
                collection_name="k_skill_collection"
            )
        else:
            vector_store.add_documents(batch)
            
    print(f"🎉 성공적으로 {len(docs)}개 K-Skill이 VectorDB({TARGET_DB_PATH})에 적재되었습니다!")

if __name__ == "__main__":
    index_k_skills()
