$ErrorActionPreference = 'Stop'
$ab = 'C:\Users\d\AppData\Roaming\npm\agent-browser.cmd'

Write-Host "Opening 8766..."
& $ab open http://127.0.0.1:8766
& $ab wait 2500

Write-Host "Filling search with saya..."
& $ab fill '#search' 'saya'
& $ab wait 1000

Write-Host "Getting word list text..."
& $ab get text '#word-list .word-item'

Write-Host "Clicking first word item..."
& $ab click '#word-list .word-item'
& $ab wait 1000

Write-Host "Getting detail word title..."
& $ab get text '.word-title'

Write-Host "Taking screenshot..."
& $ab screenshot 'C:\Users\d\Documents\open-melayu\data\audit\screenshots\test_saya.png'

Write-Host "Done test_single_session."
