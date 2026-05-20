import time
from datetime import datetime
import win32gui, win32con
import pyautogui

TARGETS = ['ERP Data Entry', 'Manual Input']

def enum_handler(hwnd, results):
    if not win32gui.IsWindowVisible(hwnd):
        return
    title = win32gui.GetWindowText(hwnd)
    if any(t in title for t in TARGETS):
        results.append((hwnd, title))

wins = []
win32gui.EnumWindows(enum_handler, wins)
if not wins:
    print('NO_WINDOW')
    raise SystemExit(1)

hwnd, title = wins[0]
# Restore and force top/front
win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 100, 100, 0, 0, win32con.SWP_NOSIZE)
win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 100, 100, 0, 0, win32con.SWP_NOSIZE)
try:
    win32gui.SetForegroundWindow(hwnd)
except Exception:
    pass

time.sleep(1.5)
rect = win32gui.GetWindowRect(hwnd)
print('RECT', rect)
# screenshot whole desktop after focus
p = rf"C:\temp\focused_erp_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
pyautogui.screenshot().save(p)
print(p)
