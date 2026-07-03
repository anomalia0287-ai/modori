#requires -version 5.1
[CmdletBinding()]
param(
    [string]$VMName = "Modori-CleanWin-QA-Direct"
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

Write-Section "VM"
$vm = Get-VM -Name $VMName -ErrorAction Stop
$vm |
    Select-Object Name, State, Generation, Uptime, CPUUsage, MemoryAssigned, AutomaticCheckpointsEnabled, CheckpointType |
    Format-List

Write-Section "Firmware"
Get-VMFirmware -VMName $VMName |
    Select-Object SecureBoot, SecureBootTemplate, BootOrder |
    Format-List

Write-Section "Hard disk"
Get-VMHardDiskDrive -VMName $VMName |
    Select-Object ControllerType, ControllerNumber, ControllerLocation, Path |
    Format-List

Write-Section "DVD"
Get-VMDvdDrive -VMName $VMName -ErrorAction SilentlyContinue |
    Select-Object ControllerType, ControllerNumber, ControllerLocation, Path |
    Format-List

Write-Section "Checkpoints"
$checkpoints = Get-VMSnapshot -VMName $VMName -ErrorAction SilentlyContinue
if ($checkpoints) {
    $checkpoints | Select-Object Name, SnapshotType, CreationTime | Format-Table -AutoSize
} else {
    Write-Host "No checkpoints"
}

Write-Section "Integration services"
Get-VMIntegrationService -VMName $VMName |
    Select-Object Name, Enabled, PrimaryStatusDescription, SecondaryStatusDescription |
    Format-Table -AutoSize

Write-Section "Summary"
if ($vm.State -eq "Running") {
    Write-Host "STATUS: VM is running"
} else {
    Write-Host "STATUS: VM is not running"
}

Write-Host "Done"
