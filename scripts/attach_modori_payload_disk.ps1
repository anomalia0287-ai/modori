#requires -version 5.1
[CmdletBinding()]
param(
    [string]$VMName = "Modori-CleanWin-QA-Direct",
    [string]$WorkspaceRoot = "C:\Users\V\Desktop\TongTong",
    [string]$PayloadRoot = "C:\VM\ModoriPayload",
    [string]$PayloadVhdPath = "C:\VM\ModoriPayload\ModoriPayloadV2.vhdx",
    [string]$LegacyPayloadVhdPath = "C:\VM\ModoriPayload\ModoriPayload.vhdx",
    [UInt64]$PayloadVhdSizeBytes = 4GB,
    [switch]$RebuildPayload
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host "== $Title ==" -ForegroundColor Cyan
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated Administrator PowerShell window."
    }
}

function Stop-TranscriptIfStarted {
    if ($script:transcriptStarted) {
        Stop-Transcript | Out-Null
        $script:transcriptStarted = $false
    }
}

function Complete-Success {
    Write-Host "Done"
    Stop-TranscriptIfStarted
    exit 0
}

$script:vhdMounted = $false

trap {
    Write-Host ""
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    if ($script:vhdMounted) {
        Dismount-VHD -Path $PayloadVhdPath -ErrorAction SilentlyContinue
        $script:vhdMounted = $false
    }
    Stop-TranscriptIfStarted
    break
}

function Assert-Path {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Label
    )
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Label was not found: $Path"
    }
}

function Assert-PayloadDriveContents {
    param([Parameter(Mandatory = $true)][string]$DriveRoot)

    $requiredPaths = @(
        (Join-Path $DriveRoot "Modori\Modori.exe"),
        (Join-Path $DriveRoot "Samples\engine-smoke-reference.xlsx"),
        (Join-Path $DriveRoot "Samples\visible-import-reference.csv"),
        (Join-Path $DriveRoot "Samples\visible-import-reference.xlsx"),
        (Join-Path $DriveRoot "Samples\visible-import-reference.sav"),
        (Join-Path $DriveRoot "Samples\visible-grid-overflow.csv"),
        (Join-Path $DriveRoot "Samples\public_data_formats\kosis-two-row.csv"),
        (Join-Path $DriveRoot "Samples\public_data_formats\cp949-public.csv"),
        (Join-Path $DriveRoot "Samples\public_data_formats\molit-deep-preamble.csv"),
        (Join-Path $DriveRoot "Samples\public_data_formats\weather-text-xls.xls"),
        (Join-Path $DriveRoot "Samples\public_data_formats\merged-public-header.xlsx"),
        (Join-Path $DriveRoot "Samples\public_data_formats\aggregate-row.csv"),
        (Join-Path $DriveRoot "Samples\public_data_formats\notice-only.xlsx"),
        (Join-Path $DriveRoot "README.txt"),
        (Join-Path $DriveRoot "QA_CONTRACT.txt"),
        (Join-Path $DriveRoot "Run-Modori.bat"),
        (Join-Path $DriveRoot "Run-Engine-Smoke-XLSX.bat"),
        (Join-Path $DriveRoot "Run-Public-Data-Smoke.bat")
    )

    foreach ($requiredPath in $requiredPaths) {
        Assert-Path -Path $requiredPath -Label "Payload content"
    }

    $engineSmokeBatch = Get-Content -LiteralPath (Join-Path $DriveRoot "Run-Engine-Smoke-XLSX.bat") -Raw
    if ($engineSmokeBatch -notmatch "engine-smoke-reference\.xlsx") {
        throw "Engine smoke batch does not reference engine-smoke-reference.xlsx"
    }
    if ($engineSmokeBatch -match "--engine-smoke.*visible-import-reference\.xlsx") {
        throw "Engine smoke batch incorrectly references the visible import workbook"
    }

    $publicDataSmokeBatch = Get-Content -LiteralPath (Join-Path $DriveRoot "Run-Public-Data-Smoke.bat") -Raw
    if ($publicDataSmokeBatch -notmatch "--public-data-smoke") {
        throw "Public data smoke batch does not run --public-data-smoke"
    }
    if ($publicDataSmokeBatch -notmatch "Samples\\public_data_formats") {
        throw "Public data smoke batch does not reference public_data_formats fixtures"
    }
    foreach ($smokeBatch in @($engineSmokeBatch, $publicDataSmokeBatch)) {
        if ($smokeBatch -notmatch "chcp 65001") {
            throw "Smoke batch does not switch the console to UTF-8 before printing JSON"
        }
    }
}

function Assert-ExistingPayloadVhd {
    param([Parameter(Mandatory = $true)][string]$Path)

    Write-Section "Validate existing payload VHDX"
    $mountedVhd = Mount-VHD -Path $Path -ReadOnly -PassThru
    $existingVhdMounted = $true
    try {
        $disk = $mountedVhd | Get-Disk
        $volume = $disk |
            Get-Partition |
            Get-Volume |
            Where-Object { $_.DriveLetter } |
            Select-Object -First 1
        if (-not $volume -or -not $volume.DriveLetter) {
            throw "Existing payload VHDX has no mounted drive letter"
        }
        $driveRoot = "$($volume.DriveLetter):\"
        Assert-PayloadDriveContents -DriveRoot $driveRoot
    } finally {
        if ($existingVhdMounted) {
            Dismount-VHD -Path $Path -ErrorAction SilentlyContinue
        }
    }
}

function Get-NewestSourceWriteTimeUtc {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    $newest = $null
    foreach ($path in $Paths) {
        $item = Get-Item -LiteralPath $path
        if ($item.PSIsContainer) {
            $newestChild = Get-ChildItem -LiteralPath $path -Recurse -File |
                Sort-Object LastWriteTimeUtc -Descending |
                Select-Object -First 1
            if ($newestChild) {
                $writeTime = $newestChild.LastWriteTimeUtc
            } else {
                $writeTime = $item.LastWriteTimeUtc
            }
        } else {
            $writeTime = $item.LastWriteTimeUtc
        }

        if (-not $newest -or $writeTime -gt $newest) {
            $newest = $writeTime
        }
    }

    return $newest
}

function Assert-PayloadVhdIsCurrent {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][datetime]$NewestSourceWriteTimeUtc
    )

    $payloadVhd = Get-Item -LiteralPath $Path
    if ($NewestSourceWriteTimeUtc -gt $payloadVhd.LastWriteTimeUtc.AddSeconds(1)) {
        throw "Existing payload VHDX is older than the packaged app; rerun this script with -RebuildPayload."
    }
}

function Backup-ExistingPayloadVhd {
    param(
        [Parameter(Mandatory = $true)][string]$PayloadVhdPath,
        [Parameter(Mandatory = $true)][string]$PayloadRoot
    )

    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    $backupPath = Join-Path $PayloadRoot "ModoriPayloadV2.before-rebuild-$timestamp.vhdx"
    if (Test-Path -LiteralPath $backupPath) {
        throw "Payload V2 backup path already exists: $backupPath"
    }

    Write-Host "Backing up existing payload VHDX to: $backupPath"
    Move-Item -LiteralPath $PayloadVhdPath -Destination $backupPath
}

Assert-Administrator

New-Item -ItemType Directory -Force -Path $PayloadRoot | Out-Null
$transcriptPath = Join-Path $PayloadRoot "attach-payload-v2.log"
$script:transcriptStarted = $false
try {
    Start-Transcript -Path $transcriptPath -Force | Out-Null
    $script:transcriptStarted = $true
    Write-Host "Log: $transcriptPath"
} catch {
    Write-Warning "Could not start transcript: $($_.Exception.Message)"
}

$sourceApp = Join-Path $WorkspaceRoot "dist\Modori"
$fixturesRoot = Join-Path $WorkspaceRoot ".visual-qa\clean-win-vm-payload"
$publicDataFixtures = Join-Path $WorkspaceRoot "tests\fixtures\public_data_formats"
$samples = @(
    (Join-Path $fixturesRoot "engine-smoke-reference.xlsx"),
    (Join-Path $fixturesRoot "visible-import-reference.csv"),
    (Join-Path $fixturesRoot "visible-import-reference.xlsx"),
    (Join-Path $fixturesRoot "visible-import-reference.sav"),
    (Join-Path $fixturesRoot "visible-grid-overflow.csv")
)

Write-Section "Preflight"
Assert-Path -Path $sourceApp -Label "Packaged app folder"
foreach ($sample in $samples) {
    Assert-Path -Path $sample -Label "Sample file"
}
Assert-Path -Path $publicDataFixtures -Label "Public data fixture folder"
$sourcePaths = @($sourceApp, $publicDataFixtures) + $samples
$newestSourceWriteTimeUtc = Get-NewestSourceWriteTimeUtc -Paths $sourcePaths

$vm = Get-VM -Name $VMName -ErrorAction Stop
Write-Host "VM: $($vm.Name) / $($vm.State)"

$attachedPayloadDisks = Get-VMHardDiskDrive -VMName $VMName |
    Where-Object { $_.Path -eq $PayloadVhdPath } |
    Select-Object

if ($RebuildPayload) {
    Write-Section "Payload rebuild requested"
    if ($vm.State -ne "Off") {
        throw "VM must be Off before rebuilding Payload V2. Shut down Windows inside the VM, wait until Hyper-V Manager shows Off, then rerun this script."
    }

    if ($attachedPayloadDisks) {
        Write-Section "Remove existing Payload V2 disk"
        foreach ($attachedPayloadDisk in $attachedPayloadDisks) {
            Remove-VMHardDiskDrive -VMHardDiskDrive $attachedPayloadDisk
            Write-Host "Removed VM disk attachment: $($attachedPayloadDisk.Path)"
        }
    }

    $legacyPayloadDisks = Get-VMHardDiskDrive -VMName $VMName |
        Where-Object { $_.Path -eq $LegacyPayloadVhdPath } |
        Select-Object
    if ($legacyPayloadDisks) {
        Write-Section "Remove legacy Payload V1 disk"
        foreach ($legacyPayloadDisk in $legacyPayloadDisks) {
            Remove-VMHardDiskDrive -VMHardDiskDrive $legacyPayloadDisk
            Write-Host "Removed legacy VM disk attachment: $($legacyPayloadDisk.Path)"
        }
    }

    if (Test-Path -LiteralPath $PayloadVhdPath) {
        Backup-ExistingPayloadVhd -PayloadVhdPath $PayloadVhdPath -PayloadRoot $PayloadRoot
    }
} elseif ($attachedPayloadDisks) {
    Assert-PayloadVhdIsCurrent -Path $PayloadVhdPath -NewestSourceWriteTimeUtc $newestSourceWriteTimeUtc
    Write-Host "Payload disk is already attached: $PayloadVhdPath"
    Complete-Success
}

if ($vm.State -ne "Off") {
    throw "VM must be Off before attaching Payload V2. Shut down Windows inside the VM, wait until Hyper-V Manager shows Off, then rerun this script."
}

if (Test-Path -LiteralPath $PayloadVhdPath) {
    Assert-PayloadVhdIsCurrent -Path $PayloadVhdPath -NewestSourceWriteTimeUtc $newestSourceWriteTimeUtc
    Assert-ExistingPayloadVhd -Path $PayloadVhdPath
    Write-Section "Attach existing payload disk"
    Add-VMHardDiskDrive -VMName $VMName -Path $PayloadVhdPath
    Write-Host "Attached existing payload disk: $PayloadVhdPath"
    Complete-Success
}

try {
    Write-Section "Create payload VHDX"
    New-VHD -Path $PayloadVhdPath -SizeBytes $PayloadVhdSizeBytes -Dynamic | Out-Null
    $mountedVhd = Mount-VHD -Path $PayloadVhdPath -PassThru
    $script:vhdMounted = $true
    $disk = $mountedVhd | Get-Disk

    Initialize-Disk -Number $disk.Number -PartitionStyle GPT
    $partition = New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
    Format-Volume -Partition $partition -FileSystem NTFS -NewFileSystemLabel "MODORIQA2" -Confirm:$false | Out-Null

    $driveRoot = "$($partition.DriveLetter):\"
    $appTarget = Join-Path $driveRoot "Modori"
    $sampleTarget = Join-Path $driveRoot "Samples"

    Write-Section "Copy files"
    New-Item -ItemType Directory -Force -Path $sampleTarget | Out-Null
    Copy-Item -LiteralPath $sourceApp -Destination $appTarget -Recurse
    Copy-Item -LiteralPath $samples -Destination $sampleTarget
    Copy-Item -LiteralPath $publicDataFixtures -Destination (Join-Path $sampleTarget "public_data_formats") -Recurse

    $readme = @"
Modori clean Windows QA payload

1. Run Run-Modori.bat to start the app.
2. Use files in the Samples folder for import tests.
3. Run Run-Engine-Smoke-XLSX.bat for a non-UI engine smoke test.
4. Run Run-Public-Data-Smoke.bat for Korean public-data import contract checks.

Expected sample files:
- Samples\engine-smoke-reference.xlsx
- Samples\visible-import-reference.csv
- Samples\visible-import-reference.xlsx
- Samples\visible-import-reference.sav
- Samples\visible-grid-overflow.csv
- Samples\public_data_formats\kosis-two-row.csv
- Samples\public_data_formats\cp949-public.csv
- Samples\public_data_formats\molit-deep-preamble.csv
- Samples\public_data_formats\weather-text-xls.xls
- Samples\public_data_formats\merged-public-header.xlsx
- Samples\public_data_formats\aggregate-row.csv
- Samples\public_data_formats\notice-only.xlsx
"@
    Set-Content -LiteralPath (Join-Path $driveRoot "README.txt") -Value $readme -Encoding ASCII

    $contract = @"
Clean Windows QA contract

Engine smoke sample:
- Samples\engine-smoke-reference.xlsx

Import visibility samples:
- Samples\visible-import-reference.csv
- Samples\visible-import-reference.xlsx
- Samples\visible-import-reference.sav
- Samples\visible-grid-overflow.csv

Public data import contract samples:
- Samples\public_data_formats\kosis-two-row.csv
- Samples\public_data_formats\cp949-public.csv
- Samples\public_data_formats\molit-deep-preamble.csv
- Samples\public_data_formats\weather-text-xls.xls
- Samples\public_data_formats\merged-public-header.xlsx
- Samples\public_data_formats\aggregate-row.csv
- Samples\public_data_formats\notice-only.xlsx

Rules:
- Run-Engine-Smoke-XLSX.bat must use only the engine smoke sample.
- Run-Public-Data-Smoke.bat must validate public-data import contracts, not just app launch.
- Run-Modori.bat is for visible UI verification.
- Visible import samples are not a substitute for engine smoke.
"@
    Set-Content -LiteralPath (Join-Path $driveRoot "QA_CONTRACT.txt") -Value $contract -Encoding ASCII

    $runModori = @"
@echo off
cd /d "%~dp0Modori"
start "" "%~dp0Modori\Modori.exe"
"@
    Set-Content -LiteralPath (Join-Path $driveRoot "Run-Modori.bat") -Value $runModori -Encoding ASCII

$engineSmoke = @"
@echo off
chcp 65001 >nul
set ROOT=%~dp0
start /wait "" "%ROOT%Modori\Modori.exe" --engine-smoke "%ROOT%Samples\engine-smoke-reference.xlsx" "%USERPROFILE%\Desktop\modori-engine-smoke.json"
set RESULT=%ERRORLEVEL%
echo Exit code: %RESULT%
echo Output: %USERPROFILE%\Desktop\modori-engine-smoke.json
if exist "%USERPROFILE%\Desktop\modori-engine-smoke.json" type "%USERPROFILE%\Desktop\modori-engine-smoke.json"
pause
exit /b %RESULT%
"@
    Set-Content -LiteralPath (Join-Path $driveRoot "Run-Engine-Smoke-XLSX.bat") -Value $engineSmoke -Encoding ASCII

$publicDataSmoke = @"
@echo off
chcp 65001 >nul
set ROOT=%~dp0
start /wait "" "%ROOT%Modori\Modori.exe" --public-data-smoke "%ROOT%Samples\public_data_formats" "%USERPROFILE%\Desktop\modori-public-data-smoke.json"
set RESULT=%ERRORLEVEL%
echo Exit code: %RESULT%
echo Output: %USERPROFILE%\Desktop\modori-public-data-smoke.json
if exist "%USERPROFILE%\Desktop\modori-public-data-smoke.json" type "%USERPROFILE%\Desktop\modori-public-data-smoke.json"
pause
exit /b %RESULT%
"@
    Set-Content -LiteralPath (Join-Path $driveRoot "Run-Public-Data-Smoke.bat") -Value $publicDataSmoke -Encoding ASCII

    Write-Section "Validate new payload contents"
    Assert-PayloadDriveContents -DriveRoot $driveRoot

    Write-Section "Dismount payload VHDX"
    Dismount-VHD -Path $PayloadVhdPath
    $script:vhdMounted = $false

    Write-Section "Attach payload disk to VM"
    Add-VMHardDiskDrive -VMName $VMName -Path $PayloadVhdPath

    Get-VMHardDiskDrive -VMName $VMName |
        Where-Object { $_.Path -eq $PayloadVhdPath } |
        Select-Object ControllerType, ControllerNumber, ControllerLocation, Path |
        Format-List

    Write-Host "Done"
} finally {
    if ($script:vhdMounted) {
        Dismount-VHD -Path $PayloadVhdPath -ErrorAction SilentlyContinue
        $script:vhdMounted = $false
    }
    Stop-TranscriptIfStarted
}
