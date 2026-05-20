Set oWS = WScript.CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' Get desktop path
desktopPath = oWS.SpecialFolders("Desktop")
shortcutPath = desktopPath & "\ERP Bot.lnk"

' Create shortcut
Set oLink = oWS.CreateShortcut(shortcutPath)
oLink.TargetPath = "c:\Trợ lý AI\launch_bot.bat"
oLink.WorkingDirectory = "c:\Trợ lý AI"
oLink.Description = "ERP Bot Assistant"
oLink.Save

WScript.Echo "Shortcut created at: " & shortcutPath
