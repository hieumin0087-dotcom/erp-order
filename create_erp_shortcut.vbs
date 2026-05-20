Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\ERP Data Entry.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "c:\Trợ lý AI\launch_erp.bat"
oLink.WorkingDirectory = "c:\Trợ lý AI"
oLink.Description = "ERP Data Entry - Influencer Order Form"
oLink.IconLocation = "shell32.dll,70"
oLink.Save

MsgBox "✅ Shortcut created on Desktop!", vbInformation, "Success"
