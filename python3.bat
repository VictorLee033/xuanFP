@echo off
rem ============================================================
rem  python3.bat —— 用项目配套的 Python 3.13 运行任意脚本
rem  用法：在项目根目录执行  python3 scripts\xxx.py
rem  （系统 python 可能指向 3.14，本脚本强制用 3.13 + pylibs）
rem ============================================================
set "PYTHONPATH=%~dp0pylibs"
"C:\Users\89689\.workbuddy\binaries\python\versions\3.13.12\python.exe" %*
