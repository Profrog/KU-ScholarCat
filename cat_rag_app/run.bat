@echo off
chcp 65001 > nul
title Solar Cat RAG Chatbot Launcher

echo ===================================================================
echo               🐱 Solar Cat RAG Chatbot Service 🐱
echo            Upstage Document Parse & Solar Pro Assistant
echo ===================================================================
echo.

set PYTHON_EXE=%USERPROFILE%\anaconda3\envs\rag_env\python.exe

if not exist "%PYTHON_EXE%" (
    echo [알림] 기본 가상환경 경로에서 찾지 못하여 시스템 python을 검색합니다: %PYTHON_EXE%
    set PYTHON_EXE=python
)

echo [INFO] 사용 파이썬: %PYTHON_EXE%
echo [INFO] 웹 브라우저에서 서비스가 열립니다 (http://localhost:8080)
echo.

"%PYTHON_EXE%" -m streamlit run app.py --server.port 8080 --server.headless false

pause
