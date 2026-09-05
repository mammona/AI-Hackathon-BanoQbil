Add-Type -AssemblyName UIAutomationClient
$root=[System.Windows.Automation.AutomationElement]::RootElement
$cw=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::NameProperty,'Extended Controls - Pixel_7:5554')
$win=$root.FindFirst([System.Windows.Automation.TreeScope]::Children,$cw)
if($win){
  foreach($id in @('ExtendedControls.stackedWidget.microphonePage.mic_allowRealAudio','ExtendedControls.stackedWidget.microphonePage.mic_inserted')){
    $ci=New-Object System.Windows.Automation.PropertyCondition([System.Windows.Automation.AutomationElement]::AutomationIdProperty,$id)
    $el=$win.FindFirst([System.Windows.Automation.TreeScope]::Descendants,$ci)
    if($el){
      $st=$el.GetCurrentPropertyValue([System.Windows.Automation.TogglePattern]::ToggleStateProperty)
      Write-Output ($id+' => ToggleState='+$st)
    } else { Write-Output ($id+' => NOT FOUND') }
  }
} else { Write-Output 'WINDOW NOT FOUND' }
