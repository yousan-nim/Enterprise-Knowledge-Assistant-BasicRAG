$ErrorActionPreference = 'Stop'

function Invoke-Docker {
    param([string[]]$DockerArguments)
    & docker @DockerArguments
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($DockerArguments -join ' ') (exit $LASTEXITCODE)"
    }
}

Push-Location (Split-Path -Parent $PSScriptRoot)
try {
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        throw 'Install Docker Desktop first and enable Linux containers.'
    }
    Invoke-Docker -DockerArguments @('compose', 'version')
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Start Docker Desktop in Linux containers mode, then run this command again.'
    }

    if (-not (Test-Path -LiteralPath '.env')) {
        $randomBytes = New-Object byte[] 24
        $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
        try {
            $generator.GetBytes($randomBytes)
        }
        finally {
            $generator.Dispose()
        }
        $password = [BitConverter]::ToString($randomBytes).Replace('-', '').ToLowerInvariant()
        $content = "POSTGRES_DB=knowledge`nPOSTGRES_USER=rag`nPOSTGRES_PASSWORD=$password`nPOSTGRES_PORT=5433`nAPI_PORT=8080`n"
        $envPath = Join-Path (Get-Location).Path '.env'
        # CreateNew refuses to overwrite a file created by another process.
        $stream = [System.IO.File]::Open($envPath, [System.IO.FileMode]::CreateNew)
        try {
            $bytes = (New-Object System.Text.UTF8Encoding($false)).GetBytes($content)
            $stream.Write($bytes, 0, $bytes.Length)
        }
        finally {
            $stream.Dispose()
        }
        Write-Host 'Created local .env with a random database password.'
    }

    Write-Host 'Building API and preparing local models. First startup downloads several GB.'
    Invoke-Docker -DockerArguments @('compose', 'config', '--quiet')
    Invoke-Docker -DockerArguments @('compose', 'up', '-d', '--build', '--wait', '--wait-timeout', '1800', 'backend')
    Invoke-Docker -DockerArguments @('compose', 'ps')
    Write-Host "Ready. Swagger is on the backend's published port (default http://127.0.0.1:8080/docs)."
    Write-Host 'Stop: docker compose down (documents and models are retained).'
}
finally {
    Pop-Location
}
