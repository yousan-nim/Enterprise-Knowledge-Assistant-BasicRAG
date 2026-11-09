$ErrorActionPreference = 'Stop'
$sourceScript = Join-Path $PSScriptRoot 'dev.ps1'
$testRoot = Join-Path ([System.IO.Path]::GetTempPath()) ('rag launcher test ' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path (Join-Path $testRoot 'scripts') -Force | Out-Null
Copy-Item -LiteralPath $sourceScript -Destination (Join-Path $testRoot 'scripts/dev.ps1')
$launcher = Join-Path $testRoot 'scripts/dev.ps1'
$envFile = Join-Path $testRoot '.env'
$originalLocation = (Get-Location).Path
$global:DockerTestCalls = @()
$global:DockerTestFail = ''

function global:docker {
    $command = $args -join ' '
    $global:DockerTestCalls += $command
    $global:LASTEXITCODE = 0
    if ($global:DockerTestFail -eq $command) { $global:LASTEXITCODE = 1 }
}

try {
    & $launcher
    $content = [System.IO.File]::ReadAllText($envFile)
    if ($content -notmatch 'POSTGRES_PASSWORD=[a-f0-9]{48}\n') { throw 'Random password generation failed.' }
    $bytes = [System.IO.File]::ReadAllBytes($envFile)
    if ($bytes[0] -eq 239) { throw '.env must not have a UTF-8 BOM.' }
    if ($global:DockerTestCalls -notcontains 'compose up -d --build --wait --wait-timeout 1800 frontend') { throw 'Startup command was not called.' }
    if ((Get-Location).Path -ne $originalLocation) { throw 'Working directory was not restored.' }

    & $launcher
    if ([System.IO.File]::ReadAllText($envFile) -ne $content) { throw 'Existing .env was overwritten.' }

    Remove-Item -LiteralPath $envFile -Force
    foreach ($failedCommand in @('info', 'compose config --quiet', 'compose up -d --build --wait --wait-timeout 1800 frontend')) {
        $global:DockerTestFail = $failedCommand
        $failed = $false
        try { & $launcher } catch { $failed = $true }
        if (-not $failed) { throw "Failure was ignored: $failedCommand" }
        if ($failedCommand -eq 'info' -and (Test-Path -LiteralPath $envFile)) { throw 'Stopped Docker must not create .env.' }
        if ((Get-Location).Path -ne $originalLocation) { throw 'Error path did not restore working directory.' }
    }
    Write-Host 'PowerShell launcher checks passed: random credentials, no BOM, spaces in path, preserved .env and Docker failure handling.'
}
finally {
    Remove-Item Function:\docker
    Remove-Variable DockerTestCalls, DockerTestFail -Scope Global
    Remove-Item -LiteralPath $testRoot -Recurse -Force
}

# Intentional Docker failure tests leave LASTEXITCODE=1; report success only after all assertions and cleanup pass.
exit 0
