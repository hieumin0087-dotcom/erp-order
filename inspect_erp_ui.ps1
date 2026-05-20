Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

function Find-WindowByName($pattern) {
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  $cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
    [System.Windows.Automation.ControlType]::Window
  )
  $wins = $root.FindAll([System.Windows.Automation.TreeScope]::Children, $cond)
  foreach ($w in $wins) {
    $name = $w.Current.Name
    if ($name -like $pattern) { return $w }
  }
  return $null
}

$win = Find-WindowByName '*ERP Data Entry*'
if (-not $win) { $win = Find-WindowByName '*Manual Input*' }
if (-not $win) { Write-Output 'NO_WINDOW'; exit 1 }
Write-Output ("WINDOW=" + $win.Current.Name)

$all = $win.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
for ($i=0; $i -lt $all.Count; $i++) {
  $el = $all.Item($i)
  $name = $el.Current.Name
  $aid = $el.Current.AutomationId
  $cls = $el.Current.ClassName
  $ctype = $el.Current.ControlType.ProgrammaticName
  if ($name -or $aid) {
    Write-Output ("TYPE=" + $ctype + " | NAME=" + $name + " | AID=" + $aid + " | CLS=" + $cls)
  }
}
