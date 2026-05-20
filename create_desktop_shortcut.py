#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Create Desktop Shortcut for ERP Data Entry"""

import os
import winshell
from win32com.client import Dispatch

desktop = winshell.desktop()
path = os.path.join(desktop, "ERP Data Entry.lnk")

target = r"c:\Trợ lý AI\launch_erp.bat"
wDir = r"c:\Trợ lý AI"
icon = r"shell32.dll"

shell = Dispatch('WScript.Shell')
shortcut = shell.CreateShortCut(path)
shortcut.Targetpath = target
shortcut.WorkingDirectory = wDir
shortcut.IconLocation = icon + ",70"
shortcut.save()

print("✅ Desktop shortcut created successfully!")
print(f"Location: {path}")
input("\nPress Enter to close...")
