@echo off
chcp 65001 > nul
title Railway One-Click Deployer

echo ===================================================================
echo               🚀 Solar Cat RAG -> Railway 클라우드 배포 🚀
echo ===================================================================
echo.
echo [1단계] Railway 로그인을 진행합니다...
echo 브라우저 창이 열리면 로그인 승인을 완료해 주세요.
echo.

call npx -y @railway/cli login

echo.
echo [2단계] 새 Railway 프로젝트를 생성/연결합니다...
call npx -y @railway/cli init

echo.
echo [3단계] Docker 컨테이너를 Railway에 빌드 및 배포합니다...
call npx -y @railway/cli up

echo.
echo [4단계] 공개 인터넷 접속 도메인을 할당합니다...
call npx -y @railway/cli domain

echo.
echo ===================================================================
echo 🎉 Railway 배포가 완료되었습니다! 상단에 표시된 도메인으로 접속하세요!
echo ===================================================================
pause
