@echo off
title iPhone Media Converter
color 0E
echo.
echo  ============================================
echo   iPhone Media Converter - Setup
echo  ============================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python not found!
    echo  Download from https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)
echo  [OK] Python found
echo.

REM Install dependencies
echo  Installing required packages...
pip install Pillow pillow-heif --quiet --upgrade
if %errorlevel% neq 0 (
    echo  [WARNING] Package install had issues. Trying with py launcher...
    py -m pip install Pillow pillow-heif --quiet --upgrade
)
echo  [OK] Python packages installed
echo.

REM Check FFmpeg
where ffmpeg >nul 2>&1
if %errorlevel% neq 0 (
    if exist "%~dp0ffmpeg.exe" (
        echo  [OK] FFmpeg found next to script
    ) else (
        echo  [WARNING] FFmpeg not found.
        echo  MOV to MP4 conversion will not work without it.
        echo  Download from: https://www.gyan.dev/ffmpeg/builds/
        echo  Place ffmpeg.exe next to this script, or add to PATH.
    )
) else (
    echo  [OK] FFmpeg found in PATH
)
echo.

echo  Launching converter...
echo.

REM Try python first, then py launcher
python "%~dp0iphone_media_converter.py"
if %errorlevel% neq 0 (
    py "%~dp0iphone_media_converter.py"
)

echo.
pause
