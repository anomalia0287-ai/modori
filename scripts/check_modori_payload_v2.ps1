#requires -version 5.1
[CmdletBinding()]
param(
    [string]$VMName = "Modori-CleanWin-QA-Direct",
    [string]$WorkspaceRoot = "C:\Users\V\Desktop\TongTong",
    [string]$PayloadVhdPath = "C:\VM\ModoriPayload\ModoriPayloadV2.vhdx",
    [string]$LogPath = "C:\VM\ModoriPayload\attach-payload-v2.log"
)

$ErrorActionPreference = "Stop"

function Write-Section {
    param([Parameter(Mandatory = $true)][string]$Title)
    Write-Host ""
    Write-Host "== $Title =="
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated Administrator PowerShell window."
    }
}

function Get-NewestSourceWriteTimeUtc {
    param([Parameter(Mandatory = $true)][string[]]$Paths)

    $newest = $null
    foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            continue
        }
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

Assert-Administrator
$WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
Write-Host "Workspace root: $WorkspaceRoot"

Write-Section "Payload VHDX file"
if (Test-Path -LiteralPath $PayloadVhdPath) {
    Get-Item -LiteralPath $PayloadVhdPath |
        Select-Object FullName, Length, LastWriteTime |
        Format-List
} else {
    Write-Host "MISSING: $PayloadVhdPath"
}

Write-Section "Payload freshness"
$sourceApp = Join-Path $WorkspaceRoot "dist\Modori"
$sourceExe = Join-Path $sourceApp "Modori.exe"
if (-not (Test-Path -LiteralPath $PayloadVhdPath)) {
    Write-Host "STATUS: Payload V2 is missing; rebuild with attach_modori_payload_disk.ps1 -RebuildPayload"
} elseif (-not (Test-Path -LiteralPath $sourceApp)) {
    Write-Host "STATUS: Packaged app folder is missing; build dist\Modori before rebuilding Payload V2"
} else {
    $payloadVhd = Get-Item -LiteralPath $PayloadVhdPath
    $newestSourceWriteTimeUtc = Get-NewestSourceWriteTimeUtc -Paths @($sourceApp)
    if (Test-Path -LiteralPath $sourceExe) {
        $sourceExeHash = (
            Get-FileHash -LiteralPath $sourceExe -Algorithm SHA256
        ).Hash.ToUpperInvariant()
        Write-Host "Packaged executable SHA-256: $sourceExeHash"
    }
    Write-Host "Packaged app newest write time UTC: $newestSourceWriteTimeUtc"
    Write-Host "Payload V2 write time UTC: $($payloadVhd.LastWriteTimeUtc)"
    if ($newestSourceWriteTimeUtc -gt $payloadVhd.LastWriteTimeUtc.AddSeconds(1)) {
        Write-Host "STATUS: Payload V2 is older than the packaged app; rerun attach_modori_payload_disk.ps1 with -RebuildPayload while the VM is Off."
    } else {
        Write-Host "STATUS: Payload V2 is current for the packaged app"
    }
}

Write-Section "Attach log"
if (Test-Path -LiteralPath $LogPath) {
    Get-Item -LiteralPath $LogPath |
        Select-Object FullName, Length, LastWriteTime |
        Format-List
    Write-Host "-- Last 80 lines --"
    Get-Content -LiteralPath $LogPath -Tail 80
} else {
    Write-Host "MISSING: $LogPath"
}

Write-Section "VM"
$vm = Get-VM -Name $VMName -ErrorAction Stop
$vm |
    Select-Object Name, State, Generation, Uptime, AutomaticCheckpointsEnabled, CheckpointType |
    Format-List

Write-Section "VM hard disks"
$hardDisks = Get-VMHardDiskDrive -VMName $VMName |
    Select-Object ControllerType, ControllerNumber, ControllerLocation, Path
$hardDisks | Format-List

Write-Section "Payload attach status"
$payloadDisk = $hardDisks |
    Where-Object { $_.Path -eq $PayloadVhdPath } |
    Select-Object -First 1
if ($payloadDisk) {
    Write-Host "STATUS: Payload V2 is attached to VM"
} else {
    Write-Host "STATUS: Payload V2 is NOT attached to VM"
}

Write-Section "Integration services"
Get-VMIntegrationService -VMName $VMName |
    Select-Object Name, Enabled, PrimaryStatusDescription, SecondaryStatusDescription |
    Format-Table -AutoSize

Write-Host ""
Write-Host "Done"
