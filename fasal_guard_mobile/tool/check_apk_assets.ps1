Add-Type -AssemblyName System.IO.Compression.FileSystem
$apk = 'build\app\outputs\flutter-apk\app-debug.apk'
$zip = [System.IO.Compression.ZipFile]::OpenRead($apk)
$zip.Entries |
  Where-Object { $_.FullName -match 'sherpa|\.onnx|\.tflite' } |
  Select-Object FullName, @{N='MB'; E={[math]::Round($_.Length/1MB,2)}} |
  Format-Table -AutoSize
$zip.Dispose()
