import pyautogui
from datetime import datetime
p = rf"C:\temp\after_read_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
pyautogui.screenshot().save(p)
print(p)
