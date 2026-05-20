@echo off
echo Dang tat Chrome hien tai...
taskkill /f /im chrome.exe 2>nul
timeout /t 2 /nobreak >nul

echo Mo Chrome voi Remote Debugging...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" ^
  --remote-debugging-port=9222 ^
  --user-data-dir="C:\Users\Admin\AppData\Local\Google\Chrome\User Data" ^
  --profile-directory=Default

timeout /t 3 /nobreak >nul
echo Chrome da mo! Bay gio chay: py "C:\Tro ly AI\erp_auto_login.py"
pause
