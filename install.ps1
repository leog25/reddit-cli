# Install reddit-cli binary for Windows.
# Usage:
#   irm https://raw.githubusercontent.com/leog25/reddit-cli-releases/main/install.ps1 | iex
#
# Options (via environment variables):
#   GITHUB_TOKEN  - Required for private repos
#   VERSION       - Pin to a specific tag (e.g. v0.3.0). Default: latest
#   INSTALL_DIR   - Override install path. Default: ~\.local\bin
#   REPO          - Override repo. Default: leog25/reddit-cli
#Requires -Version 5.1
$ErrorActionPreference = 'Stop'

$Repo = if ($env:REPO) { $env:REPO } else { "leog25/reddit-cli" }
$InstallDir = if ($env:INSTALL_DIR) { $env:INSTALL_DIR } else { "$env:USERPROFILE\.local\bin" }
$Version = if ($env:VERSION) { $env:VERSION } else { "latest" }
$Artifact = "reddit-windows-x64.exe"

# ── Auth headers (required for private repos) ────────────────────────

$Headers = @{}
if ($env:GITHUB_TOKEN) {
    $Headers["Authorization"] = "token $env:GITHUB_TOKEN"
}

# ── Resolve version ──────────────────────────────────────────────────

if ($Version -eq "latest") {
    Write-Host "Resolving latest release..."
    $ReleaseUrl = "https://api.github.com/repos/$Repo/releases/latest"
    try {
        $Release = Invoke-RestMethod -Uri $ReleaseUrl -Headers $Headers -UseBasicParsing
        $Tag = $Release.tag_name
    } catch {
        Write-Error "Could not resolve latest release. If this is a private repo, set `$env:GITHUB_TOKEN"
        exit 1
    }
    Write-Host "Latest release: $Tag"
} else {
    $Tag = $Version
}

# ── Download ──────────────────────────────────────────────────────────

New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
$Dest = Join-Path $InstallDir "reddit.exe"

Write-Host "Downloading $Artifact -> $Dest..."

if ($env:GITHUB_TOKEN) {
    # Private repo: resolve asset URL via API
    $TagUrl = "https://api.github.com/repos/$Repo/releases/tags/$Tag"
    $TagRelease = Invoke-RestMethod -Uri $TagUrl -Headers $Headers -UseBasicParsing
    $Asset = $TagRelease.assets | Where-Object { $_.name -eq $Artifact } | Select-Object -First 1
    if ($Asset) {
        $AssetHeaders = @{
            "Authorization" = "token $env:GITHUB_TOKEN"
            "Accept" = "application/octet-stream"
        }
        Invoke-WebRequest -Uri $Asset.url -Headers $AssetHeaders -OutFile $Dest -UseBasicParsing
    } else {
        $DirectUrl = "https://github.com/$Repo/releases/download/$Tag/$Artifact"
        Invoke-WebRequest -Uri $DirectUrl -Headers $Headers -OutFile $Dest -UseBasicParsing
    }
} else {
    $DirectUrl = "https://github.com/$Repo/releases/download/$Tag/$Artifact"
    Invoke-WebRequest -Uri $DirectUrl -OutFile $Dest -UseBasicParsing
}

# ── Smoke test ────────────────────────────────────────────────────────

$TestResult = & $Dest --help 2>&1
if ($LASTEXITCODE -ne 0) {
    Remove-Item -Force $Dest
    Write-Error "Binary failed smoke test"
    exit 1
}

Write-Host "Installed reddit.exe to $Dest"

# ── PATH check ────────────────────────────────────────────────────────

$UserPath = [Environment]::GetEnvironmentVariable('Path', 'User')
if ($UserPath -notlike "*$InstallDir*") {
    Write-Host ""
    Write-Host "Adding $InstallDir to your PATH..."
    [Environment]::SetEnvironmentVariable('Path', "$InstallDir;$UserPath", 'User')
    $env:Path = "$InstallDir;$env:Path"
    Write-Host "Done. Restart your terminal or run:"
    Write-Host "  `$env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')"
}
