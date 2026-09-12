@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

REM ===== 证书与密码（如需更换在此修改）=====
set PFX=%~dp0certs\codesign.pfx
set PWD=20100622xu
set EXE=%~dp0dist\SFS_Pack_Tool_v22_Embedded_GPL.exe
set DESC=SFS Pack Tool v22

echo ==========================================================
echo   SFS Pack Tool v22 - 代码签名（signtool）
echo ==========================================================

if not exist "%EXE%" ( echo 未找到 %EXE% ，请先运行 build.bat 打包 & exit /b 1 )
if not exist "%PFX%"  ( echo 未找到证书 %PFX% ，请将 pfx 放入 certs\ & exit /b 1 )

REM 自动定位 signtool（Windows SDK）。若某个 SDK 版本号找不到，请把下面路径中的版本号改成你机器上 bin 目录里的实际版本。
set "SIGNTOOL="
where signtool >nul 2>nul && set "SIGNTOOL=signtool"
if not defined SIGNTOOL (
  for /d %%K in ("%ProgramFiles(x86)%\Windows Kits\10\bin\*") do (
    if exist "%%K\x64\signtool.exe" if not defined SIGNTOOL set "SIGNTOOL=%%K\x64\signtool.exe"
  )
)
if not defined SIGNTOOL (
  echo 未找到 signtool.exe，请安装 Windows SDK（勾选"Windows SDK for Desktop C++ x86 Apps"），
  echo 或把 signtool 所在目录加入 PATH，再重跑本脚本。
  exit /b 1
)

echo 使用签名工具：%SIGNTOOL%

"%SIGNTOOL%" sign /f "%PFX%" /p %PWD% /fd SHA256 /t http://timestamp.digicert.com /d "%DESC%" /du "https://github.com/aaaa111ssf/SFS-Pack-Mod-Tools" "%EXE%"
if errorlevel 1 ( echo 签名失败，请检查：证书密码 / signtool 是否可用 / 网络时间戳 & exit /b 1 )

echo 验证签名 ...
"%SIGNTOOL%" verify /pa /v "%EXE%" | findstr /i "Cert Hash SHA256" >nul
echo.
echo 签名完成，证书主体：CN=AFuturestar
exit /b 0