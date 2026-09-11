# 한국 주식/ETF 실시간 투자 분석 및 브리핑

## What this skill does
네이버 증권 오픈 API를 활용하여, 국내 주식(삼성전자, SK하이닉스 등) 및 ETF의 실시간 시세, 외국인/기관 매매동향, 증권사 컨센서스 목표주가, PER/PBR 밸류에이션 데이터를 종합 분석하고 투자 모멘텀 점수를 산출합니다. (출처: Profrog/stock-advisor 모듈 기반)

## When to use
- "삼성전자 현재 주가랑 증권사 목표가, 수급 현황 알려줘"
- "SK하이닉스 PER이랑 외인 기관 매매동향 브리핑해줘"
- "현대차 주식 투자 지표랑 밸류에이션 어때?"
- "국내 반도체나 2차전지 관련주 시세 분석해줘"

## Inputs & Execution
```bash
python scripts/run_stock.py --query "삼성전자" --json
python scripts/run_stock.py --code "000660" --json
```

- `--query`: 종목명 (삼성전자, SK하이닉스, 현대차, NAVER, 카카오, LG에너지솔루션 등)
- `--code`: 6자리 종목코드 (005930, 000660 등)
