@echo off
chcp 65001 > nul
title Cloudflare Tunnel Launcher

echo ===================================================================
echo             🌐 Solar Cat RAG -> Cloudflare 실시간 배포 🌐
echo ===================================================================
echo.
echo [INFO] 로컬 챗봇(http://localhost:8080)을 Cloudflare 글로벌 엣지 네트워크로 연결합니다...
echo [INFO] 발급되는 https://*.trycloudflare.com 도메인을 통해 전 세계 어디서든 접속 가능합니다!
echo.

.\cloudflared.exe tunnel --url http://localhost:8080

pause
