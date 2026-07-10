param(
    [string]$Version = "0.1.0",
    [switch]$SkipInstaller,
    [switch]$SkipPortable,
    [switch]$SkipDependencyInstall
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$AppName = -join ([char[]](0x91D1, 0x5E01, 0x51B2, 0x523A))
$DistDir = Join-Path $ProjectRoot "dist"
$ReleaseDir = Join-Path $ProjectRoot "release"
$AppDir = Join-Path $DistDir $AppName
$PortableZip = Join-Path $ReleaseDir "$AppName-portable-$Version.zip"
$SpecFile = Join-Path $ProjectRoot "installer\windows_pyinstaller.spec"
$InnoScript = Join-Path $ProjectRoot "installer\windows_setup.iss"

Set-Location $ProjectRoot

function Compress-DirectoryWithRetry {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )

    for ($attempt = 1; $attempt -le 5; $attempt += 1) {
        try {
            Compress-Archive -Path $SourcePath -DestinationPath $DestinationPath -Force -ErrorAction Stop
            return
        } catch {
            if ($attempt -eq 5) {
                throw
            }
            Start-Sleep -Seconds 2
        }
    }
}

function Remove-PathWithRetry {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    for ($attempt = 1; $attempt -le 5; $attempt += 1) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            if ($attempt -eq 5) {
                throw
            }
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $SkipDependencyInstall) {
    python -m pip install -r requirements.txt -r requirements-build.txt
    if ($LASTEXITCODE -ne 0) {
        throw "Dependency installation failed."
    }
}

Remove-PathWithRetry -Path (Join-Path $ProjectRoot "build")
Remove-PathWithRetry -Path $AppDir
New-Item -ItemType Directory -Force $ReleaseDir | Out-Null

python scripts\make_windows_icon.py
if ($LASTEXITCODE -ne 0) {
    throw "Icon generation failed."
}
python -m PyInstaller --noconfirm --clean $SpecFile
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

if (-not (Test-Path (Join-Path $AppDir "$AppName.exe"))) {
    throw "PyInstaller did not create the expected exe: $AppDir\$AppName.exe"
}

if (-not $SkipPortable) {
    Remove-Item -LiteralPath $PortableZip -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Compress-DirectoryWithRetry -SourcePath (Join-Path $AppDir "*") -DestinationPath $PortableZip
    Write-Host "Portable package created: $PortableZip"
}

if (-not $SkipInstaller) {
    $iscc = Get-Command "ISCC.exe" -ErrorAction SilentlyContinue
    if (-not $iscc) {
        $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        if (Test-Path $candidate) {
            $iscc = Get-Item $candidate
        }
    }

    if ($iscc) {
        $env:APP_VERSION = $Version
        & $iscc.Source $InnoScript
        if ($LASTEXITCODE -ne 0) {
            throw "Inno Setup installer generation failed."
        }
        Write-Host "Installer output directory: $ReleaseDir"
    } else {
        Write-Warning "ISCC.exe was not found. Inno Setup installer generation was skipped."
    }
}

Write-Host "Windows build finished: $AppDir"
