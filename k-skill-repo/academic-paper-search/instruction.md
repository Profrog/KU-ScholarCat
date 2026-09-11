# 최신 첨단 산업 논문 & 고려대학교 dCollection 학위논문 검색 & 도서관 EzProxy 연동

## What this skill does
1. **고려대학교 공식 dCollection(디지털 학술정보 유통시스템) 석·박사 학위논문 및 교내 학술 연구 실시간 검색**:
   - 고려대 대학원 석·박사 학위논문 검색 및 dCollection 상세 페이지(`https://dcollection.korea.ac.kr/srch/srchDetail/{id}`), 영구식별자(`dcollection.net/handler/korea/{id}`) 원문 열람 링크 제공.
   - 저자, 지도교수, 학과/전공, 학위(석사/박사), 발행년도, 키워드(NWDAF, 5G, AI/ML 등), 초록(Abstract) 상세 추출.
   - dCollection 논문 ID(예: `000000270210`)나 URL 직접 조회 완벽 지원.
2. **OpenAlex 글로벌 오픈 학술 데이터베이스 검색 & 산업 영향도 점수 분석**:
   - 첨단 기술(반도체, AI, 2차전지, 통신/6G, 바이오 등)의 글로벌 저널/컨퍼런스 최신 논문 검색 및 산업화 가능성 분석.
3. **고려대학교 도서관 교외접속(EzProxy) 연동**:
   - 해외 유료 저널(IEEE, ACM, ScienceDirect, Springer, Nature 등)을 고려대 대학원생/교직원 라이선스로 열람할 수 있는 `ku_proxy_url` 제공.

## When to use
- "고려대학교 석박사 학위논문 중 5G 패킷코어나 NWDAF 관련 논문 찾아줘"
- "dCollection 000000270210 논문 상세 내용과 원문 링크 알려줘"
- "고려대 쪽 논문 서칭할 때 dCollection 디지털 학술정보 유통시스템 논문 검색해줘"
- "HBM이나 2나노 반도체 최신 논문 트렌드와 고려대 도서관 열람 링크 알려줘"
- "LLM 에이전트 관련 최신 글로벌 연구 논문과 고려대 도서관 EzProxy 링크 찾아줘"

## Inputs & Execution
```bash
python scripts/run_papers.py --query "NWDAF" --n 3 --json
python scripts/run_papers.py --query "000000270210" --json
python scripts/run_papers.py --sector 통신 --query "5G 패킷코어" --n 3 --json
python scripts/run_papers.py --sector 반도체 --n 3 --json
```
