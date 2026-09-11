FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치 (ChromaDB 컴파일 및 한글 지원)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

# 의존성 복사 및 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 및 기본 벡터 DB 복사
COPY . .

# 업로드 폴더 생성
RUN mkdir -p uploads

# 포트 노출
EXPOSE 8080

# 컨테이너 실행 (Railway 동적 PORT 환경변수 지원)
CMD ["sh", "-c", "streamlit run app.py --server.port=${PORT:-8080} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
