@echo off
REM TrOCR Model Downloader - Smart-Audit-Agent
REM Downloads the TrOCR handwriting recognition model from HuggingFace

echo.
echo ============================================================
echo   TrOCR Model Downloader - Smart-Audit-Agent
echo ============================================================
echo.

REM Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: PowerShell is required but not found.
    pause
    exit /b 1
)

REM Run the PowerShell script
powershell -ExecutionPolicy Bypass -File "%~dp0download_trocr.ps1"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Download failed. Please check your internet connection.
    pause
    exit /b 1
)

echo.
echo Press any key to exit...
pause >nul
