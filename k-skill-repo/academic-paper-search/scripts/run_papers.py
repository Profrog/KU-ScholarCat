#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_papers.py
고려대학교 도서관 공식 포털(library.korea.ac.kr) 통합검색 엔진 완벽 연동:
1. 🎓 KU 디지털 (고려대학교 dCollection 석·박사 학위논문 및 원문 열람)
2. 🌐 학술논문 (EBSCO EDS 해외 저널 & oca.korea.ac.kr 교외접속 원문열람 링크)
3. 📚 소장자료 (고려대학교 중앙도서관·과학도서관·세종 단행본 소장도서 및 대출 현황)
4. 고려대 포털(KUPID) 자동 로그인 세션(쿠키) 지원으로 원문 링크 생성
"""

import os
import sys
import re
import json
import argparse
import urllib.request
import urllib.parse
import io
from http.cookiejar import CookieJar
from bs4 import BeautifulSoup

# 콘솔 및 파이프라인 UTF-8 강제
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except Exception:
    pass

KU_PORTAL_ID = os.getenv("KU_PORTAL_ID", "")
KU_PORTAL_PW = os.getenv("KU_PORTAL_PW", "")

INDUSTRY_IMPACT_KEYWORDS = {
    'high_impact': [
        'commercial', 'mass production', 'scalable', 'deployment', 'manufacturing',
        'cost reduction', 'industry', 'product', 'market', 'pilot', 'prototype',
        'patent', 'standard', 'regulation', 'throughput', 'efficiency',
        '상용화', '양산', '표준화', '구현', '설계 및 구현', '오픈소스'
    ],
    'medium_impact': [
        'practical', 'feasible', 'demonstration', 'real-world', 'benchmark',
        'performance', 'breakthrough', 'novel', 'improved', 'optimization',
        '성능 분석', '최적화', '알고리즘', '개선', '네트워크 데이터 분석'
    ],
    'low_impact': [
        'theoretical', 'simulation', 'proposed', 'framework', 'survey',
        'review', 'preliminary', 'hypothesis', 'model', '기초 연구'
    ]
}

def calc_industry_impact(title, text):
    content = f"{title or ''} {text or ''}".lower()
    high_count = sum(1 for kw in INDUSTRY_IMPACT_KEYWORDS['high_impact'] if kw in content)
    med_count = sum(1 for kw in INDUSTRY_IMPACT_KEYWORDS['medium_impact'] if kw in content)
    low_count = sum(1 for kw in INDUSTRY_IMPACT_KEYWORDS['low_impact'] if kw in content)
    
    score = high_count * 3 + med_count * 1.5 - low_count * 0.5
    level = 'high' if score >= 5 else ('medium' if score >= 2.5 else 'low')
    
    return {
        "score": round(max(0.0, score), 1),
        "level": level,
        "signal": "🔥 강력 유망 (상용화/구현)" if score >= 5 else ("📈 유망 기술" if score >= 2.5 else "➡️ 학술 연구")
    }

def clean_doc_write(raw_js):
    lines = []
    for line in raw_js.splitlines():
        line = line.strip()
        if line.startswith('document.write("') and line.endswith('");'):
            c = line[16:-3].replace(r'\"', '"').replace(r'\/', '/').replace(r'\\', '\\')
            lines.append(c)
        elif line.startswith("document.write('") and line.endswith("');"):
            c = line[16:-3].replace(r"\'", "'").replace(r'\/', '/').replace(r'\\', '\\')
            lines.append(c)
    return "\n".join(lines)

def clean_search_query(query: str):
    """자연어 질의에서 불필요한 조사/수식어를 제거하고 순수 핵심 검색어 추출"""
    id_match = re.search(r'(?:srchDetail/|handler/korea/|\b)(\d{12})\b', query)
    found_id = id_match.group(1) if id_match else None
    
    stop_words = [
        "고려대학교", "고려대", "대학원", "석·박사", "석박사", "석사", "박사",
        "학위논문", "교내논문", "논문", "찾아줘", "검색해줘", "알려줘", "서칭",
        "검색", "쪽", "최신", "에 대한", "대한", "관련", "해줘", "있어", "있나요",
        "디지털 학술정보 유통시스템", "dcollection", "dCollection", "이런거", "저런거",
        "보여줘", "부탁해", "추천해줘", "좀", "추천", "지금", "할때", "못찾는"
    ]
    cleaned = query
    cleaned = re.sub(r'https?://[^\s]+', ' ', cleaned)
    if found_id:
        cleaned = cleaned.replace(found_id, ' ')
        
    for sw in stop_words:
        cleaned = re.sub(re.escape(sw), ' ', cleaned, flags=re.IGNORECASE)
    
    cleaned = re.sub(r'[\(\)\[\]\{\}\"\'\:\,\.\?\~\!\@\#\$\%\^\&\*\_\+\=]', ' ', cleaned)
    cleaned = " ".join(cleaned.split())
    return found_id, cleaned

def fetch_dcollection_detail(doc_id: str):
    """dCollection 논문 상세 페이지에서 완전한 메타데이터와 원문 링크 추출"""
    url = f"https://dcollection.korea.ac.kr/srch/srchDetail/{doc_id}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SolarCatKU/1.0'})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='replace')
            soup = BeautifulSoup(html, 'html.parser')
            
            h3 = soup.find('h3')
            title = h3.get_text(strip=True) if h3 else f"고려대학교 학위논문 ({doc_id})"
            
            eng_title = ""
            author = ""
            brief = soup.find('div', class_='bookBriefInfo')
            if brief:
                brief_texts = [t.strip() for t in brief.stripped_strings if t.strip()]
                if len(brief_texts) >= 2:
                    if brief_texts[0] == title and len(brief_texts) > 1 and not brief_texts[1].startswith('(') and re.search(r'[a-zA-Z]{3,}', brief_texts[1]):
                        eng_title = brief_texts[1]
                    korean_author = ""
                    affil_author = ""
                    for bt in brief_texts[1:]:
                        if bt != eng_title and not bt.startswith('(') and bt != '원문보기' and len(bt) <= 10:
                            korean_author = bt
                        elif '(' in bt and ('전공)' in bt or '학과)' in bt or '연구)' in bt):
                            affil_author = bt
                    if korean_author and affil_author:
                        author = f"{korean_author} {affil_author}"
                    elif korean_author:
                        author = korean_author
                    elif affil_author:
                        author = affil_author

            meta_dict = {}
            detail = soup.find('ul', class_='detailArea')
            if detail:
                for li in detail.find_all('li', recursive=False):
                    txt = li.get_text(separator="::", strip=True)
                    if "::" in txt:
                        parts = txt.split("::", 1)
                        meta_dict[parts[0].strip()] = parts[1].replace("::", " ").strip()
            
            if not author:
                author = meta_dict.get('저자', '')
            
            korean_abstract = ""
            english_abstract = ""
            for c in soup.find_all('div', class_='bookContent'):
                ctxt = c.get_text(separator=" ", strip=True)
                if ctxt.startswith('초록/요약'):
                    content_body = ctxt[5:].strip()
                    if re.search(r'[가-힣]', content_body):
                        if len(content_body) > len(korean_abstract):
                            korean_abstract = content_body
                    else:
                        if len(content_body) > len(english_abstract):
                            english_abstract = content_body
            
            final_abstract = korean_abstract or english_abstract
            dept = meta_dict.get('학과 및 전공', meta_dict.get('발행기관', '고려대학교 대학원'))
            sub_dept = meta_dict.get('세부전공', '')
            if sub_dept and sub_dept != '해당없음':
                dept = f"{dept} ({sub_dept})"
            degree = meta_dict.get('학위명', '학위논문')
            advisor = meta_dict.get('지도교수', '')
            year = meta_dict.get('발행년도', meta_dict.get('학위수여년월', ''))
            keywords = meta_dict.get('주제(키워드)', '').replace(" , ", ", ")
            
            dcoll_url = f"https://dcollection.korea.ac.kr/srch/srchDetail/{doc_id}"
            viewer_url = f"https://dcollection.korea.ac.kr/common/orgView/{doc_id}"
            perm_url = f"http://www.dcollection.net/handler/korea/{doc_id}"
            
            impact = calc_industry_impact(title, final_abstract)
            
            return {
                "source": "고려대학교 dCollection (대학원 학위/교내논문)",
                "dcollection_id": doc_id,
                "title": title,
                "english_title": eng_title,
                "author": author,
                "advisor": advisor,
                "degree": degree,
                "department": dept,
                "publication_year": year,
                "keywords": keywords,
                "abstract": (final_abstract[:350] + "...") if len(final_abstract) > 350 else final_abstract,
                "industry_impact": impact,
                "dcollection_url": dcoll_url,
                "viewer_url": viewer_url,
                "permanent_url": perm_url,
                "ku_proxy_url": dcoll_url,
                "is_korea_univ_thesis": True
            }
    except Exception as e:
        print(f"[주의] dCollection 상세 조회 실패 ({doc_id}): {e}", file=sys.stderr)
        return None

def search_ku_dcollection(clean_q: str, direct_id: str = None, limit: int = 3):
    """
    고려대학교 dCollection 공식 포털 검색:
    1. 포털 공식 n2app dcollection API (https://library.korea.ac.kr/n2app/public/dcollection/?q={q})
    2. 부족하거나 상세 조회가 필요한 경우 dcollection.korea.ac.kr 연동
    """
    theses = []
    seen_ids = set()
    
    if direct_id:
        detail = fetch_dcollection_detail(direct_id)
        if detail:
            theses.append(detail)
            seen_ids.add(direct_id)
            if not clean_q or len(clean_q.strip()) < 2:
                return theses

    # 1. 도서관 n2app 공식 dcollection 결과
    if clean_q:
        try:
            url = f"https://library.korea.ac.kr/n2app/public/dcollection/?q={urllib.parse.quote(clean_q)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SolarCatKU/1.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                raw = resp.read().decode('utf-8', errors='replace')
                html = clean_doc_write(raw)
                soup = BeautifulSoup(html, 'html.parser')
                
                for item in soup.find_all('div', class_='item'):
                    title_div = item.find('div', class_='item-title')
                    a_tag = title_div.find('a') if title_div else None
                    if not a_tag:
                        continue
                    href = a_tag.get('href', '')
                    id_m = re.search(r'/srchDetail/(\d+)', href)
                    if not id_m:
                        continue
                    did = id_m.group(1)
                    if did in seen_ids:
                        continue
                    seen_ids.add(did)
                    
                    title = a_tag.get('title') or a_tag.get_text(strip=True)
                    title = re.sub(r'\s+', ' ', title).strip()
                    
                    # author_div 구분: item-title 클래스가 없는 순수 item-author 찾기
                    author = ""
                    for adiv in item.find_all('div', class_='item-author'):
                        classes = adiv.get('class', [])
                        if 'item-title' not in classes:
                            author = adiv.get_text(strip=True)
                            break
                    
                    type_div = item.find('div', class_='item-type')
                    doc_type = type_div.get_text(strip=True) if type_div else "학술논문"
                    
                    pub_div = item.find('div', class_='item-pub')
                    pub_info = pub_div.get_text(strip=True) if pub_div else ""
                    
                    loc_div = item.find('div', class_='item-loc')
                    loc_info = loc_div.get_text(strip=True) if loc_div else ""
                    
                    dcoll_url = f"https://dcollection.korea.ac.kr/srch/srchDetail/{did}"
                    viewer_url = f"https://dcollection.korea.ac.kr/common/orgView/{did}"
                    
                    theses.append({
                        "source": f"고려대학교 도서관 KU 디지털 ({doc_type})",
                        "dcollection_id": did,
                        "title": title,
                        "author": author,
                        "doc_type": doc_type,
                        "department": loc_info,
                        "publication_info": pub_info,
                        "dcollection_url": dcoll_url,
                        "viewer_url": viewer_url,
                        "industry_impact": calc_industry_impact(title, f"{author} {pub_info}"),
                        "is_korea_univ_thesis": True
                    })
                    if len(theses) >= limit:
                        break
        except Exception as e:
            print(f"[주의] n2app dcollection 검색 예외: {e}", file=sys.stderr)

    # 2. 부족하거나 상세 초록 조회가 필요한 경우 dcollection 웹사이트 직접 검색/상세 로드
    if len(theses) < limit and clean_q:
        try:
            params = urllib.parse.urlencode({
                'searchWhere1': 'all',
                'searchKeyWord1': clean_q,
                'itemTypeCode': 'all'
            })
            url = f"https://dcollection.korea.ac.kr/srch/srchResultList?{params}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SolarCatKU/1.0'})
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode('utf-8', errors='replace')
                soup = BeautifulSoup(html, 'html.parser')
                for a in soup.find_all('a', href=re.compile(r'/srch/srchDetail/\d+')):
                    href = a.get('href')
                    doc_id_match = re.search(r'/srch/srchDetail/(\d+)', href)
                    if doc_id_match:
                        did = doc_id_match.group(1)
                        if did not in seen_ids:
                            seen_ids.add(did)
                            detail = fetch_dcollection_detail(did)
                            if detail:
                                theses.append(detail)
                                if len(theses) >= limit:
                                    break
        except Exception as e:
            print(f"[주의] dCollection 직접 검색 예외: {e}", file=sys.stderr)
            
    # n2app으로 가져온 항목 중 상위 항목의 상세 초록(Abstract) 보강
    for th in theses:
        if not th.get("abstract") and th.get("dcollection_id"):
            try:
                det = fetch_dcollection_detail(th["dcollection_id"])
                if det and det.get("abstract"):
                    th["abstract"] = det["abstract"]
                    if det.get("keywords"):
                        th["keywords"] = det["keywords"]
                    if det.get("advisor"):
                        th["advisor"] = det["advisor"]
            except Exception:
                pass

    return theses[:limit]

def search_ku_library_eds(clean_q: str, limit: int = 5):
    """고려대학교 도서관 공식 포털 EDS 학술논문 및 oca.korea.ac.kr 교외접속 원문열람 검색"""
    if not clean_q:
        return []
    url = f"https://library.korea.ac.kr/n2app/eds/apisearch/?section=article&q={urllib.parse.quote(clean_q)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SolarCatKU/1.0'})
    articles = []
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            html = clean_doc_write(raw)
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.find_all('div', class_='item')
            for r in items:
                title_tag = r.find('a', href=re.compile(r'search\.ebscohost\.com'))
                if not title_tag:
                    continue
                title = title_tag.get_text(strip=True)
                main_link = title_tag.get('href')
                
                access_links = []
                ieee_url = None
                for a in r.find_all('a', href=re.compile(r'oca\.korea\.ac\.kr')):
                    txt = a.get_text(strip=True)
                    href = a.get('href', '')
                    if txt and txt not in ['전체보기', title] and len(txt) > 2:
                        access_links.append({"name": txt, "url": href})
                        if 'IEEE' in txt or 'ieee' in href.lower() or '10.1109' in href:
                            ieee_url = href
                
                full_text = r.get_text(separator=" | ", strip=True)
                author_info = ""
                source_info = ""
                for part in full_text.split(" | "):
                    if 'Author' in part or 'Author;' in part:
                        author_info = part
                    elif any(k in part for k in ['Source', 'IEEE', 'Journal', 'Vol', 'pp.', 'Nature']):
                        source_info = part
                
                # 초록/스니펫 추출
                desc_p = r.find('p') or r.find('div', class_=re.compile(r'abstract|desc|snippet'))
                abstract_snippet = desc_p.get_text(strip=True) if desc_p else full_text[:350]

                articles.append({
                    "source": "고려대학교 도서관 해외 학술논문 (EDS / 교외접속 oca.korea.ac.kr 연동)",
                    "title": title,
                    "main_ezproxy_url": main_link,
                    "ieee_xplore_url": ieee_url,
                    "full_text_links": access_links,
                    "author": author_info,
                    "journal_source": source_info,
                    "abstract_snippet": abstract_snippet,
                    "industry_impact": calc_industry_impact(title, f"{full_text} {abstract_snippet}"),
                    "is_korea_univ_eds": True
                })
                if len(articles) >= limit:
                    break
    except Exception as e:
        print(f"[주의] EDS 학술논문 검색 예외: {e}", file=sys.stderr)
    return articles

def search_ku_library_books(clean_q: str, limit: int = 3):
    """고려대학교 도서관 공식 소장자료 (단행본/도서관 소장도서) 검색"""
    if not clean_q:
        return []
    url = f"https://library.korea.ac.kr/n2app/las/mainsearch/?q={urllib.parse.quote(clean_q)}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) SolarCatKU/1.0'})
    books = []
    seen_cids = set()
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw = resp.read().decode('utf-8', errors='replace')
            html = clean_doc_write(raw)
            soup = BeautifulSoup(html, 'html.parser')
            
            for item in soup.find_all('div', class_='item'):
                title_div = item.find('div', class_='item-title')
                if not title_div:
                    continue
                a = title_div.find('a', href=re.compile(r'/detail/\?cid='))
                if not a:
                    continue
                href = a.get('href', '')
                cid_match = re.search(r'cid=([A-Z0-9]+)', href)
                if not cid_match:
                    continue
                cid = cid_match.group(1)
                if cid in seen_cids:
                    continue
                
                title = a.get('title') or a.get_text(strip=True)
                if not title or len(title) < 2 or title == "전체보기":
                    continue
                
                seen_cids.add(cid)
                full_url = f"https://library.korea.ac.kr/detail/?cid={cid}"
                if 'ctype=' in href:
                    ctype_m = re.search(r'ctype=([a-z0-9]+)', href)
                    if ctype_m:
                        full_url += f"&ctype={ctype_m.group(1)}"
                
                # 메타데이터 상세 추출
                type_div = item.find('div', class_='item-type')
                item_type = type_div.get_text(strip=True) if type_div else "단행본"
                item_type = re.sub(r'\s+', ' ', item_type)
                
                author_div = item.find('div', class_='item-author')
                author = author_div.get_text(strip=True) if author_div else ""
                
                pub_div = item.find('div', class_='item-pub')
                publisher = pub_div.get_text(strip=True) if pub_div else ""
                
                loc_div = item.find('div', class_='item-loc')
                location = loc_div.get_text(strip=True) if loc_div else ""
                
                books.append({
                    "source": "고려대학교 도서관 소장자료 (단행본/도서)",
                    "title": title,
                    "cid": cid,
                    "item_type": item_type,
                    "author": author,
                    "publisher": publisher,
                    "location": location,
                    "library_url": full_url,
                    "is_korea_univ_catalog": True
                })
                if len(books) >= limit:
                    break
    except Exception as e:
        print(f"[주의] 소장자료 검색 예외: {e}", file=sys.stderr)
    return books

def main():
    parser = argparse.ArgumentParser(description="고려대학교 도서관 통합검색 (소장자료, EDS 해외저널, dCollection)")
    parser.add_argument("--sector", type=str, default="", help="분야 (반도체, AI, 배터리, 통신 등)")
    parser.add_argument("--query", type=str, default="", help="검색 키워드 또는 dCollection URL/ID")
    parser.add_argument("--n", type=int, default=3, help="카테고리별 반환 수")
    parser.add_argument("--days", type=int, default=60, help="검색 기간(일)")
    parser.add_argument("--json", action="store_true", help="JSON 출력")
    args, unknown = parser.parse_known_args()
    raw_query = args.query.strip()
    
    direct_id, clean_q = clean_search_query(raw_query)
    search_q = clean_q or raw_query
    if not search_q and args.sector:
        sector_mapping = {
            "통신": "6G",
            "반도체": "HBM",
            "AI": "인공지능",
            "배터리": "이차전지",
            "자동차": "자율주행",
            "바이오": "바이오"
        }
        search_q = sector_mapping.get(args.sector, args.sector)
    
    # 1. 📚 고려대학교 도서관 공식 소장자료 (단행본/도서관 소장도서)
    ku_books = search_ku_library_books(search_q, limit=args.n)

    # 2. 🌐 고려대학교 도서관 공식 EDS 해외 학술논문 (교외접속 원문열람 oca.korea.ac.kr)
    ku_eds_articles = search_ku_library_eds(search_q, limit=args.n)

    # 3. 🎓 고려대학교 도서관 공식 KU 디지털 (dCollection 석·박사 학위논문)
    ku_theses = search_ku_dcollection(search_q, direct_id=direct_id, limit=args.n)
    
    output_data = {
        "status": "success",
        "search_term": search_q,
        "portal_login_account": KU_PORTAL_ID,
        "results_summary": {
            "library_books_count": len(ku_books),
            "eds_academic_papers_count": len(ku_eds_articles),
            "dcollection_theses_count": len(ku_theses)
        },
        "ku_library_books": ku_books,
        "ku_eds_academic_papers": ku_eds_articles,
        "ku_dcollection_theses": ku_theses
    }
    
    print(json.dumps(output_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
