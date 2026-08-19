@echo off
rem ============================================================
rem  修复 python 环境（一次性）：把 Python 3.13 加到用户 PATH 最前面，
rem  让命令行里的 `python` 命令重新指向 3.13（而非 D 盘的 3.14）。
rem  运行后请【关闭并重新打开】命令行窗口再验证：python --version
rem ============================================================
echo.
echo  正在把 Python 3.13 加入用户 PATH ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='C:\Users\89689\.workbuddy\binaries\python\versions\3.13.12'; $cur=[Environment]::GetEnvironmentVariable('Path','User'); if($cur -like '*'+$p+'*'){Write-Host '  已存在，无需重复添加'} else {[Environment]::SetEnvironmentVariable('Path', $p+';'+$cur, 'User'); Write-Host '  添加成功'}"
echo.
echo  完成！请关闭本窗口，并【重新打开一个新的命令行窗口】，
echo  然后运行  python --version  应显示 3.13。
echo.
pause
