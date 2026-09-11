@echo off
chcp 65001 > nul
title Solar Cat KU Service Launcher

echo ===================================================================
echo             🐱 Solar Cat KU Service Launcher 🐾
echo     고려대학교 학술·논문 & 120+ 한국 특화 K-Skill AI 어시스턴트
echo ===================================================================
echo.

set PYTHON_EXE=%USERPROFILE%\anaconda3\envs\rag_env\python.exe

if not exist "%PYTHON_EXE%" (
    echo [알림] 가상환경 python을 기본 환경에서 찾습니다.
    set PYTHON_EXE=python
)

cd /d "%~dp0cat_rag_app"

echo [INFO] 사용 파이썬: %PYTHON_EXE%
echo [INFO] Solar Cat KU 웹 서버를 시작합니다... (http://localhost:8080)
echo.

"%PYTHON_EXE%" -m streamlit run app.py --server.port 8080 --server.headless false

pause
