@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==========================================================
echo  SFS Pack Tool v22 - one-click BUILD + SIGN
echo  (single ASCII-safe script, no encoding issues)
echo ==========================================================

REM ---- 1) AssetRipper ----
if exist "third_party\assetripper-1.1.4\AssetRipper.GUI.Free.exe" (
    echo [1/4] AssetRipper already present, skip unzip
) else (
    echo [1/4] Extracting AssetRipper 1.1.4 ...
    if not exist "third_party\assetripper-1.1.4" mkdir "third_party\assetripper-1.1.4"
    powershell -NoProfile -Command "Expand-Archive -Force -Path 'AssetRipper_win_x64-1.1.4.zip' -DestinationPath 'third_party\assetripper-1.1.4'"
    if errorlevel 1 ( echo    FAILED to unzip. Check AssetRipper_win_x64-1.1.4.zip & pause & exit /b 1 )
)

REM ---- 2) deps ----
echo [2/4] Checking build dependencies ...
python -m PyInstaller --version >nul 2>nul
if not errorlevel 1 (
    echo    PyInstaller OK
) else (
    echo    PyInstaller missing, installing online ...
    python -m pip install --upgrade pyinstaller UnityPy
    if errorlevel 1 ( echo    pip install failed. Run manually then retry. & pause & exit /b 1 )
)

if not exist "licenses" mkdir "licenses"
if not exist "licenses\LICENSE-GPL-3.0.txt" copy /y "LICENSE-GPL-3.0.txt" "licenses\" >nul
if not exist "licenses\GPL_COMPLIANCE.md" copy /y "GPL_COMPLIANCE.md" "licenses\" >nul

REM ---- 3) build ----
echo [3/4] Building EXE with PyInstaller ...
python -m PyInstaller --noconfirm --clean SFS_Pack_Tool_v22.spec
if errorlevel 1 ( echo    BUILD FAILED. See output above. & pause & exit /b 1 )

REM ---- 4) sign ----
echo [4/4] Signing ...
set "PFX=%~dp0certs\codesign.pfx"
set "PWD=20100622xu"
set "EXE=%~dp0dist\SFS_Pack_Tool_v22_Embedded_GPL.exe"
set "SIGNTOOL="
where signtool >nul 2>nul && set "SIGNTOOL=signtool"
if not defined SIGNTOOL (
  for /d %%K in ("%ProgramFiles(x86)%\Windows Kits\10\bin\*") do (
    if exist "%%K\x64\signtool.exe" if not defined SIGNTOOL set "SIGNTOOL=%%K\x64\signtool.exe"
  )
)
if not defined SIGNTOOL (
    echo    signtool not found. Install Windows SDK or add to PATH. Skipping sign.
) else (
    "%SIGNTOOL%" sign /f "%PFX%" /p %PWD% /fd SHA256 /t http://timestamp.digicert.com /d "SFS Pack Tool v22" /du "https://github.com/aaaa111ssf/SFS-Pack-Mod-Tools" "%EXE%"
    if errorlevel 1 ( echo    SIGN FAILED. Check pfx/password/network. & pause & exit /b 1 )
    echo    Verify signature ...
    "%SIGNTOOL%" verify /pa /v "%EXE%" >nul 2>nul && echo    Verify OK || echo    Verify incomplete
)

echo.
echo ==========================================================
echo  DONE. EXE = %cd%\dist\SFS_Pack_Tool_v22_Embedded_GPL.exe
echo ==========================================================
if exist "%EXE%" dir /b dist\*.exe
pause
exit /b 0