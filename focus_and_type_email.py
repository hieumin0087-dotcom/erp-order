import time
import pyautogui
import pygetwindow as gw
import win32gui

EMAIL = 'georgeschirra@aol.com'

def find_window():
    titles = gw.getAllTitles()
    for t in titles:
        if 'ERP Data Entry' in t or 'Manual Input' in t:
            wins = gw.getWindowsWithTitle(t)
            if wins:
                return wins[0]
    return None

win = find_window()
if not win:
    print('NO_WINDOW')
    raise SystemExit(1)

hwnd = win._hWnd
win32gui.ShowWindow(hwnd, 9)
try:
    win32gui.SetForegroundWindow(hwnd)
except Exception:
    pass

time.sleep(1.5)
left, top = win.left, win.top
print('RECT', left, top, win.width, win.height)
pyautogui.click(left + 260, top + 120)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.1)
pyautogui.press('backspace')
time.sleep(0.1)
pyautogui.write(EMAIL, interval=0.03)
time.sleep(0.4)
pyautogui.click(left + 470, top + 120)
print('DONE')
