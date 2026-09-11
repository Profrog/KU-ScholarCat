"""
codex_backend.py
로컬 Codex CLI(`codex exec`)를 LLM 백엔드로 사용하는 어댑터.

개인용(단일 사용자) 목적. Gemini API 크레딧을 쓰지 않고, 이 환경에 로그인된
Codex(OpenAI provider)를 subprocess 로 호출하여 답변 텍스트를 얻는다.

- `--output-last-message` 로 최종 답변만 파일에 받아 ANSI/메타 잡음 없이 파싱한다.
- 스트리밍은 지원하지 않으므로, 전체 답변을 받아 제너레이터로 흘려보낸다.
"""

import os
import shutil
import tempfile
import subprocess


CODEX_BIN = os.getenv("CODEX_BIN") or shutil.which("codex") or "codex"
CODEX_MODEL = os.getenv("CODEX_MODEL", "")  # 비우면 codex 기본 모델 사용
CODEX_TIMEOUT = int(os.getenv("CODEX_TIMEOUT", "120"))


def is_available() -> bool:
    """codex 실행 파일이 존재하는지 확인."""
    return bool(shutil.which(CODEX_BIN) or os.path.exists(CODEX_BIN))


def run_codex(prompt: str, timeout: int = None) -> str:
    """
    codex exec 를 비대화형으로 호출하여 최종 답변 텍스트를 반환한다.
    실패 시 예외를 던진다(호출 측에서 폴백 처리).
    """
    timeout = timeout or CODEX_TIMEOUT
    with tempfile.NamedTemporaryFile("r", suffix=".txt", delete=False, encoding="utf-8") as tf:
        out_path = tf.name

    cmd = [
        CODEX_BIN, "exec",
        "--skip-git-repo-check",
        "--color", "never",
        "--ephemeral",
        "-o", out_path,
    ]
    if CODEX_MODEL:
        cmd += ["-m", CODEX_MODEL]
    cmd += [prompt]

    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        with open(out_path, "r", encoding="utf-8") as f:
            answer = f.read().strip()

        if not answer:
            # 최종 메시지 파일이 비면 stdout 에서 최대한 건짐
            raise RuntimeError(
                f"codex 응답이 비어 있음 (rc={proc.returncode}): {proc.stderr[:300]}"
            )
        return answer
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def stream_codex(prompt: str, timeout: int = None):
    """
    codex 응답을 한 번에 받아 청크 단위로 흘려보내는 제너레이터.
    (codex exec 는 실시간 토큰 스트리밍을 제공하지 않으므로 유사 스트리밍)
    """
    answer = run_codex(prompt, timeout=timeout)
    chunk = 24
    for i in range(0, len(answer), chunk):
        yield answer[i:i + chunk]
