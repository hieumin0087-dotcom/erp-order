import time
import pyautogui

EMAIL='georgeschirra@aol.com'
# verified from screenshot after focus
input_x, input_y = 202, 378
btn_x, btn_y = 355, 376

pyautogui.click(input_x, input_y)
time.sleep(0.2)
pyautogui.hotkey('ctrl','a')
time.sleep(0.1)
pyautogui.press('backspace')
time.sleep(0.1)
pyautogui.write(EMAIL, interval=0.03)
time.sleep(0.3)
pyautogui.click(btn_x, btn_y)
print('DONE')
