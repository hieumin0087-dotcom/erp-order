"""
Script to create desktop shortcut for ERP Bot
"""
import os
import winshell
from win32com.client import Dispatch

desktop = winshell.desktop()
path = os.path.join(desktop, "ERP Bot.lnk")

target = r"c:\Trợ lý AI\launch_bot.bat"
icon = r"c:\Trợ lý AI\launch_bot.bat"

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(path)
shortcut.Targetpath = target
shortcut.WorkingDirectory = r"c:\Trợ lý AI"
shortcut.IconLocation = icon
shortcut.save()

print(f"✅ Đã tạo shortcut trên Desktop: {path}")
