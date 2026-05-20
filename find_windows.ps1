Get-Process |
  Where-Object { $_.MainWindowTitle -and $_.MainWindowTitle.Trim().Length -gt 0 } |
  Select-Object ProcessName, Id, MainWindowTitle, Path |
  Sort-Object MainWindowTitle |
  Format-Table -AutoSize
