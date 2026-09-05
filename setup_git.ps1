$env:Path = "C:\Program Files\Git\cmd;" + $env:Path
Set-Location d:\Faisal-shield\fasal_guard_mobile

Write-Output "=== Git Init ==="
git init

Write-Output "=== Config ==="
git config user.name "mammona"
git config user.email "mammona@users.noreply.github.com"

Write-Output "=== Git Add ==="
git add .

Write-Output "=== Git Status ==="
git status --short | Select-Object -First 30

Write-Output "=== Done ==="
