@echo off
setlocal enabledelayedexpansion
title xuanFP Stock Workstation
cd /d "%~dp0"

rem ============================================================
rem  xuanFP - One-click start (foreground, auto-restart on crash)
rem  Double-click to start the backend and open the browser.
rem  Closing this window stops the service.
rem  If port 8710 is already in use, just opens the browser.
rem ============================================================

rem ---------- 1. check port 8710 ----------
netstat -ano | findstr /c:":8710" | findstr /c:"LISTENING" >nul 2>nul
if %errorlevel%==0 (
    echo.
    echo   [OK] xuanFP already running. Opening browser...
    start "" "http://127.0.0.1:8710/"
    timeout /t 3 >nul
    exit /b 0
)

rem ---------- 2. locate python (prefer bundled 3.13, else PATH) ----------
set "PYTHONPATH=%~dp0pylibs"
set "PY="
if exist "C:\Users\89689\.workbuddy\binaries\python\versions\3.13.12\python.exe" (
    set "PY=C:\Users\89689\.workbuddy\binaries\python\versions\3.13.12\python.exe"
)
if not defined PY (
    where python >nul 2>nul
    if !errorlevel!==0 set "PY=python"
)
if not defined PY (
    echo.
    echo   [ERROR] Python not found. Please install Python 3.10-3.13.
    pause
    exit /b 1
)

rem ---------- 3. verify the chosen python can load deps ----------
"%PY%" -c "import uvicorn" >nul 2>nul
if !errorlevel! neq 0 (
    echo.
    echo   [ERROR] Python cannot load dependencies. pylibs missing or wrong version.
    echo           Run:  python3 scripts\fetch_deps.py  to rebuild pylibs.
    pause
    exit /b 1
)

echo.
echo  ==============================================
echo    xuanFP Stock Workstation
echo    Starting backend service (auto-restart on crash)...
echo    Browser will open  http://127.0.0.1:8710/
echo    Close this window to stop the service
echo  ==============================================
echo.

rem ---------- 4. delayed browser open (6s) ----------
start "" /min cmd /c "timeout /t 6 /nobreak >nul & start http://127.0.0.1:8710/"

rem ---------- 5. run server in foreground, restart on crash ----------
:run_loop
"%PY%" -m uvicorn backend.main:app --host 127.0.0.1 --port 8710
echo.
echo   [INFO] Service stopped. Restarting in 5 seconds... (close this window to stop)
timeout /t 5 /nobreak >nul
goto run_loop
