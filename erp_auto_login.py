import webbrowser
import time
import pyautogui
import pyperclip

ERP_MAIN = "https://erp.bx123.pro/admin/main"

def erp_login():
    print("[ERP] Mo ERP tren Chrome cua sep...")
    
    # Mo trang main, neu chua login no se tu dong redirect ve trang login
    webbrowser.open(ERP_MAIN)
    
    # Cho 4 giay de trang web tai xong
    print("[ERP] Cho 4 giay de trang tai hoan tat...")
    time.sleep(4)
    
    # Kiem tra URL hien tai xem co phai la trang Login khong
    # Boom Ctrl+L de chon thanh dia chi, copy URL
    pyautogui.hotkey('ctrl', 'l')
    time.sleep(0.2)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.2)
    pyautogui.press('esc') # Bo chon thanh dia chi
    
    current_url = pyperclip.paste().lower()
    try:
        print(f"[ERP] URL dang hien thi tren Chrome: {current_url[:150]}")
    except Exception:
        print("[ERP] URL co ky tu dac biet, dang xu ly...")
    
    if "login" in current_url:
        print("[ERP] Chua dang nhap! (Chrome da luu san Mat khau)")
        print("[ERP] Phat hien trang Login. Dang tu dong bam nut Login bang ma lenh...")
        
        # Chon lai thanh dia chi
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.2)
        
        # Go chu "javascript:" (Chrome khong cho paste chu nay nen phai tu dong gao)
        pyautogui.write("javascript:")
        time.sleep(0.1)
        
        # Paste phan lenh bam nut Login an
        js_code = "document.querySelector('button[type=submit], .btn-success').click(); void(0);"
        pyperclip.copy(js_code)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.2)
        
        # Nhan Enter de chay lenh
        pyautogui.press('enter')
        print("[ERP] Da Auto-Click Login thanh cong!")
        
    else:
        print("[ERP] DA DANG NHAP ROI. Khong bam them gi nua de tranh an nham!")
        print("[ERP] Xong phim.")

if __name__ == "__main__":
    erp_login()
