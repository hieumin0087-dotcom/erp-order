import os
import sys

desktop = os.path.join(os.path.expanduser("~"), "Desktop")

vbs_content = '''Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = "''' + desktop + '''\\ERP Bot.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "c:\\Trợ lý AI\\launch_bot.bat"
oLink.WorkingDirectory = "c:\\Trợ lý AI"
oLink.Save
'''

vbs_path = "temp_shortcut.vbs"
with open(vbs_path, "w") as f:
    f.write(vbs_content)

print("Done. Double-click temp_shortcut.vbs to create shortcut.")

sys.exit(0)
