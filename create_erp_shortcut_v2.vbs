Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.SpecialFolders("Desktop") & "\Trợ lý lên đơn.lnk"
Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = "c:\Trợ lý AI\launch_erp.bat"
oLink.WorkingDirectory = "c:\Trợ lý AI"
oLink.Description = "Trợ lý lên đơn - ERP Data Entry"
oLink.IconLocation = "shell32.dll,70"
oLink.Save
