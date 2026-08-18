@echo off
cd /d %~dp0
set PYTHONPATH=%~dp0pylibs
echo 启动 xuanFP 后端... 浏览器访问 http://127.0.0.1:8710/
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8710
pause
