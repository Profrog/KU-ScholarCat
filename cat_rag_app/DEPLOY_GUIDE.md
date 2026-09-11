# 🚀 Solar Cat RAG: Cloudflare & Railway 배포 가이드

본 프로젝트는 **Cloudflare**와 **Railway** 두 가지 클라우드 환경에 최적화되어 패키징되었습니다.

---

## 🌐 1. Cloudflare 실시간 배포 (즉시 접속 가능!)

현재 Cloudflare Tunnel이 실시간으로 가동 중이며, 전 세계 어디서든 바로 접속하실 수 있습니다:

👉 **[https://attendance-headphones-estimate-operators.trycloudflare.com](https://attendance-headphones-estimate-operators.trycloudflare.com)**

- **특징**: 별도의 도메인 구매나 복잡한 DNS 설정 없이 무료 HTTPS 보안 도메인이 제공됩니다.
- **재실행 방법**: 언제든 `cat_rag_app` 폴더 내의 [`deploy_cloudflare.bat`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/deploy_cloudflare.bat) 파일을 더블 클릭하시면 됩니다.

---

## 🚂 2. Railway 클라우드 배포

독립적인 24시간 상시 가동 컨테이너 서버가 필요하신 경우 Railway를 사용하실 수 있습니다.
이미 모든 배포 파일([`Dockerfile`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/Dockerfile), [`railway.json`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/railway.json), [`Procfile`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/Procfile), [`requirements.txt`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/requirements.txt))이 준비되어 있습니다.

### 방법 A. 원클릭 스크립트로 배포
[`deploy_railway.bat`](file:///c:/Users/rapad/OneDrive/Desktop/langgraph/cat_rag_app/deploy_railway.bat) 파일을 더블 클릭합니다:
1. 웹 브라우저가 열리면 Railway 계정으로 로그인 승인합니다.
2. 자동으로 프로젝트가 생성되고 Docker 컨테이너가 Railway 클라우드에 빌드 & 배포됩니다.
3. 고유 도메인이 생성되어 즉시 접속 가능합니다.

### 방법 B. GitHub 레포지토리 연동 배포 (권장)
1. 본 폴더(`cat_rag_app`)를 본인의 GitHub 레포지토리에 푸시합니다:
   ```bash
   git remote add origin https://github.com/당신의계정/cat_rag_app.git
   git push -u origin master
   ```
2. [Railway 대시보드(railway.app)](https://railway.app)에 접속하여 **`+ New Project`** 클릭
3. **`Deploy from GitHub repo`** 선택 후 해당 레포지토리 선택
4. **Variables (환경변수)** 탭에서 다음을 추가:
   - `UPSTAGE_API_KEY`: ``
5. **Settings** -> **Networking**에서 `Generate Domain`을 클릭하면 상시 접속 가능한 고유 URL이 발급됩니다!
