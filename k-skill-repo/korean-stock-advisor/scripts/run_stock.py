#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_stock.py
네이버 증권 API를 조회하여 종목별 시세, 수급, 목표가, 밸류에이션 종합 분석을 수행합니다.
(Profrog/stock-advisor 기반)
"""

import sys
import json
import argparse
import urllib.request
import urllib.parse
import io

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
except Exception:
    pass

STOCK_NAME_TO_CODE = {
    "삼성전자": "005930",
    "SK하이닉스": "000660",
    "LG에너지솔루션": "373220",
    "현대차": "005380",
    "NAVER": "035420",
    "네이버": "035420",
    "카카오": "035720",
    "삼성SDI": "006400",
    "LG화학": "051910",
    "포스코퓨처엠": "003670",
    "POSCO홀딩스": "005490",
    "포스코": "005490",
    "에코프로비엠": "247540",
    "셀트리온": "068270",
    "기아": "000270",
    "한미반도체": "042700",
    "KODEX 200": "069500",
    "KODEX 코스닥150": "229200",
    "KODEX 반도체": "091160",
    "KODEX 2차전지산업": "305720"
}

def fetch_stock_data(code):
    url = f"https://m.stock.naver.com/api/stock/{code}/integration"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 SolarCatStock/1.0"})
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return None

def analyze_stock(code_or_name):
    code = STOCK_NAME_TO_CODE.get(code_or_name, code_or_name)
    if not code.isdigit():
        # 검색 시도
        for name, c in STOCK_NAME_TO_CODE.items():
            if code_or_name in name or name in code_or_name:
                code = c
                break
                
    if not code.isdigit() or len(code) != 6:
        return {"status": "error", "message": f"유효한 6자리 종목코드를 찾을 수 없습니다: {code_or_name}"}
        
    data = fetch_stock_data(code)
    if not data:
        return {"status": "error", "message": f"네이버 증권 데이터를 불러올 수 없습니다 (종목코드: {code})"}
        
    basic = data.get("totalInfos", [])
    val_map = {}
    for item in basic:
        k = item.get("key")
        v = item.get("value")
        if k and v:
            val_map[k] = v
            
    # 시세 기본 정보
    deal_trends = data.get("dealTrendInfos", [])
    latest_deal = deal_trends[0] if deal_trends else {}
    
    consensus = data.get("consensusInfo", {}) or {}
    target_price = consensus.get("priceTargetMean", "N/A")
    target_opinion = consensus.get("recommMean", "N/A")
    
    # 최근 5영업일 외인/기관 수급
    foreign_net = 0
    organ_net = 0
    for d in deal_trends[:5]:
        f_q = d.get("foreignerPureBuyQuant", "0").replace(",", "").replace("+", "")
        o_q = d.get("organPureBuyQuant", "0").replace(",", "").replace("+", "")
        try:
            foreign_net += int(f_q)
            organ_net += int(o_q)
        except:
            pass
            
    close_price = latest_deal.get("closePrice", "0")
    change_ratio = latest_deal.get("compareToPreviousPrice", {}).get("text", "보합")
    diff = latest_deal.get("compareToPreviousClosePrice", "0")
    
    # 간이 모멘텀 점수 산정 (Profrog stock-advisor 기반)
    score = 50.0
    # 수급 반영
    if foreign_net > 0: score += 10.0
    else: score -= 5.0
    if organ_net > 0: score += 10.0
    else: score -= 5.0
    
    # 컨센서스 목표가 괴리율 반영
    upside_str = "N/A"
    try:
        cur_p = float(close_price.replace(",", ""))
        tgt_p = float(target_price.replace(",", ""))
        upside = round(((tgt_p - cur_p) / cur_p) * 100, 1)
        upside_str = f"+{upside}%" if upside > 0 else f"{upside}%"
        if upside > 20: score += 15.0
        elif upside > 10: score += 8.0
    except:
        pass
        
    # 투자의견 (4.0 이상 매수)
    try:
        op = float(target_opinion)
        if op >= 4.0: score += 10.0
    except:
        pass
        
    return {
        "status": "success",
        "종목코드": code,
        "현재가": f"{close_price}원",
        "전일대비": f"{diff}원 ({change_ratio})",
        "밸류에이션": {
            "PER": val_map.get("PER", val_map.get("추정PER", "N/A")),
            "PBR": val_map.get("PBR", "N/A"),
            "ROE": val_map.get("ROE", "N/A"),
            "배당수익률": val_map.get("배당수익률", "N/A")
        },
        "증권사_컨센서스": {
            "목표주가": f"{target_price}원" if target_price != "N/A" else "N/A",
            "상승여력": upside_str,
            "투자의견점수": f"{target_opinion} / 5.0 (매수의견)" if target_opinion != "N/A" else "N/A"
        },
        "수급동향_최근5일": {
            "외국인순매수_합계": f"{foreign_net:+,}주",
            "기관순매수_합계": f"{organ_net:+,}주"
        },
        "어드바이저_종합점수": round(score, 1),
        "투자시그널": "🟢 적극 매수 유망" if score >= 75 else ("📈 긍정적 관심" if score >= 55 else "➡️ 중립/관망")
    }

def get_active_market_leaders():
    """
    네이버 증권 시세/수급 우수 종목군 실시간 분석 (대형주 & 주요 섹터 주도주)
    """
    leaders = []
    # 주요 대표 종목들 중 당일 상승/모멘텀 우수 종목 스캔
    target_list = [
        ("SK하이닉스", "000660", "반도체/HBM"),
        ("한미반도체", "042700", "반도체 패키징/TC본더"),
        ("삼성전자", "005930", "메모리/파운드리"),
        ("현대차", "005380", "SDV/자율주행/수소"),
        ("LG에너지솔루션", "373220", "2차전지/배터리"),
        ("에코프로비엠", "247540", "양극재/이차전지"),
        ("셀트리온", "068270", "바이오시밀러/ADC"),
        ("NAVER", "035420", "생성형 AI/클라우드"),
        ("KODEX 200", "069500", "코스피 대형주 ETF")
    ]
    
    for name, code, sector in target_list:
        res = analyze_stock(code)
        if res and res.get("status") == "success":
            res["종목명"] = name
            res["관련섹터"] = sector
            leaders.append(res)
            
    # 모멘텀 점수 및 등락률 순 정렬
    leaders.sort(key=lambda x: x.get("어드바이저_종합점수", 0), reverse=True)
    return {
        "status": "success",
        "market_scan_time": "실시간",
        "top_market_leaders": leaders[:5]
    }

def main():
    parser = argparse.ArgumentParser(description="한국 주식/ETF 실시간 투자 분석기")
    parser.add_argument("--query", type=str, default="", help="종목명 (예: 삼성전자, SK하이닉스, 실시간, 상승주)")
    parser.add_argument("--code", type=str, default="", help="6자리 종목코드")
    parser.add_argument("--leaders", action="store_true", help="실시간 시장 주도주/상승주 스캔")
    parser.add_argument("--json", action="store_true", default=True, help="JSON 출력")
    
    args, unknown = parser.parse_known_args()
    
    if args.leaders or any(k in args.query for k in ["상승", "급등", "주도주", "실시간", "시장"]):
        result = get_active_market_leaders()
    else:
        target = args.code if args.code else (args.query or "삼성전자")
        result = analyze_stock(target)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
