import pyautogui
from datetime import datetime
p = rf"C:\temp\desktop_capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
img = pyautogui.screenshot()
img.save(p)
print(p)
