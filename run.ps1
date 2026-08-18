# xuanFP 一键启动脚本
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$env:PYTHONPATH = "$root\pylibs"
Write-Host "启动 xuanFP 后端... 浏览器访问 http://127.0.0.1:8710/"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8710
