@echo off
echo ========================================
echo ERP Bot - Quick Launch
echo ========================================
echo.
set /p EMAIL="Nhap email nguoi gui: "
set /p URL="Nhap URL ERP: "
echo.
echo Dang xu ly...
cd /d "c:\Trợ lý AI"
py bot_erp_cli.py %EMAIL% %URL%
echo.
pause
