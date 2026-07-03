#requires -version 5.1
[CmdletBinding()]
param(
    [string]$VMName = "Modori-CleanWin-QA-Direct",
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

Assert-Administrator

Write-Section "Payload VHDX file"
if (Test-Path -LiteralPath $PayloadVhdPath) {
    Get-Item -LiteralPath $PayloadVhdPath |
        Select-Object FullName, Length, LastWriteTime |
        Format-List
} else {
    Write-Host "MISSING: $PayloadVhdPath"
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
