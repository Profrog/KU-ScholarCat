# -*- coding: utf-8 -*-
"""
네이버 뉴스 검색 K-Skill 실행 스크립트
k-skill-proxy 경유로 최신 뉴스 기사 검색 (인증키 불필요)
"""
import sys
import io
import json
import argparse
import urllib.parse
import urllib.request

# UTF-8 콘솔 출력 보장
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

PROXY_URL = "https://k-skill-proxy.nomadamas.org/v1/naver-news/search"

def search_news(query: str, display: int = 5, sort: str = "sim"):
    params = {
        "q": query,
        "display": min(max(display, 1), 20),
        "sort": sort
    }
    url = f"{PROXY_URL}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data
    except Exception as e:
        return {"error": str(e), "items": []}

def main():
    parser = argparse.ArgumentParser(description="Naver News Search via k-skill-proxy")
    parser.add_argument("--query", "-q", required=True, help="Search query keyword")
    parser.add_argument("--display", "-n", type=int, default=5, help="Number of items to return")
    parser.add_argument("--sort", default="sim", choices=["sim", "date"], help="Sort method")
    parser.add_argument("--json", action="store_true", help="Output JSON format")
    args = parser.parse_args()

    result = search_news(args.query, args.display, args.sort)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        items = result.get("items", [])
        print(f"=== 네이버 뉴스 검색 결과 (검색어: {args.query}, 건수: {len(items)}) ===")
        for i, it in enumerate(items, 1):
            title = it.get("title", "").strip()
            desc = it.get("description", "").strip()
            link = it.get("originallink") or it.get("link", "")
            pub = it.get("pub_date", "")
            print(f"[{i}] {title} ({pub})")
            print(f"    - 요약: {desc}")
            print(f"    - 링크: {link}\n")

if __name__ == "__main__":
    main()
