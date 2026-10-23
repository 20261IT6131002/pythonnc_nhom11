@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
    py -m venv .venv
    if errorlevel 1 goto :error
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :error
if not exist .env (
    copy .env.example .env >nul
    echo Sua cau hinh MySQL trong .env roi chay lai.
    pause
    exit /b 1
)
.venv\Scripts\python.exe main.py
if errorlevel 1 goto :error
exit /b 0
:error
echo Co loi. Kiem tra file README.md.
pause
exit /b 1
