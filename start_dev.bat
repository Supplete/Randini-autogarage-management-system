@echo off
title Randini Auto Garage - Development Server
color 0A
echo.
echo ========================================
echo   Randini Auto Garage Development
echo ========================================
echo.

echo [1] Start Django Server Only
echo [2] Install/Update Dependencies
echo [3] Open Setup Guide
echo [4] Exit
echo.
set /p choice="Choose an option (1-4): "

if "%choice%"=="1" goto django_only
if "%choice%"=="2" goto install_deps
if "%choice%"=="3" goto open_guide
if "%choice%"=="4" goto exit

:django_only
echo.
echo Starting Django development server...
echo Local URL: http://localhost:8000
echo.
python manage.py runserver
goto end

:install_deps
echo.
echo Installing/Updating dependencies...
echo.
pip install -r requirements.txt
echo.
echo Dependencies installed successfully!
pause
goto start

:open_guide
echo.
echo Opening Setup Guide...
start SETUP_GUIDE.md
goto start

:exit
echo.
echo Goodbye!
exit

:end
echo.
echo Server stopped. Press any key to exit...
pause >nul
