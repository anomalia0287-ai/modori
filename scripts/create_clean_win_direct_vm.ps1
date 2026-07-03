#requires -version 5.1
[CmdletBinding()]
param(
    [string]$VMName = "Modori-CleanWin-QA-Direct",
    [string]$OldVMName = "Modori-CleanWin-QA",
    [string]$VMRoot = "C:\VM\ModoriCleanWinDirect",
    [string]$IsoPath = "C:\VM\ISO\Win11_25H2_Korean_x64_v2.iso",
    [UInt64]$VhdSizeBytes = 80GB,
    [UInt64]$MemoryStartupBytes = 4GB,
    [UInt64]$MemoryMinimumBytes = 2GB,
    [UInt64]$MemoryMaximumBytes = 6GB,
    [int]$ProcessorCount = 2,
    [string]$SwitchName = "Default Switch",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "Continue"

function Write-Step {
    param([Parameter(Mandatory = $true)][string]$Message)
    Write-Host ""
    Write-Host "== $Message ==" -ForegroundColor Cyan
}

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated Administrator PowerShell window."
    }
}

function Assert-CommandExists {
    param([Parameter(Mandatory = $true)][string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command was not found: $Name"
    }
}

$vhdPath = Join-Path $VMRoot "$VMName.vhdx"
$transcriptPath = Join-Path $env:TEMP ("modori-direct-vm-{0:yyyyMMdd-HHmmss}.log" -f (Get-Date))
$isoMountedByScript = $false
$vhdMounted = $false

Start-Transcript -Path $transcriptPath -Force | Out-Null

try {
    Write-Step "Preflight checks"
    Assert-Administrator
    Assert-CommandExists -Name "Get-VM"
    Assert-CommandExists -Name "New-VM"
    Assert-CommandExists -Name "New-VHD"
    Assert-CommandExists -Name "Mount-DiskImage"
    Assert-CommandExists -Name "Get-WindowsImage"

    if (-not (Test-Path -LiteralPath $IsoPath)) {
        throw "ISO file was not found: $IsoPath"
    }

    $isoItem = Get-Item -LiteralPath $IsoPath
    if ($isoItem.Length -lt 6GB) {
        throw "ISO file is unexpectedly small: $($isoItem.Length) bytes"
    }

    if (Get-VM -Name $VMName -ErrorAction SilentlyContinue) {
        throw "Target VM already exists: $VMName. Stopping to avoid overwriting existing state."
    }

    if (Test-Path -LiteralPath $vhdPath) {
        throw "Target VHDX already exists: $vhdPath. Stopping to avoid overwriting existing state."
    }

    $switch = Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue
    if (-not $switch) {
        $availableSwitches = (Get-VMSwitch | Select-Object -ExpandProperty Name) -join ", "
        throw "Virtual switch was not found: $SwitchName. Available switches: $availableSwitches"
    }

    $oldVM = Get-VM -Name $OldVMName -ErrorAction SilentlyContinue
    if ($oldVM -and $oldVM.State -ne "Off") {
        Write-Step "Power off old failed VM"
        Write-Host "Old VM '$OldVMName' will be powered off, not deleted."
        Stop-VM -Name $OldVMName -TurnOff -Force
    }

    New-Item -ItemType Directory -Path $VMRoot -Force | Out-Null

    Write-Step "Mount ISO"
    $diskImage = Get-DiskImage -ImagePath $IsoPath
    if (-not $diskImage.Attached) {
        Mount-DiskImage -ImagePath $IsoPath | Out-Null
        $isoMountedByScript = $true
        $diskImage = Get-DiskImage -ImagePath $IsoPath
    }

    $isoVolume = $diskImage | Get-Volume | Select-Object -First 1
    if (-not $isoVolume -or -not $isoVolume.DriveLetter) {
        throw "Could not determine the mounted ISO drive letter."
    }

    $isoRoot = "$($isoVolume.DriveLetter):\"
    $installWim = Join-Path $isoRoot "sources\install.wim"
    $installEsd = Join-Path $isoRoot "sources\install.esd"
    if (Test-Path -LiteralPath $installWim) {
        $installImage = $installWim
    } elseif (Test-Path -LiteralPath $installEsd) {
        $installImage = $installEsd
    } else {
        throw "Could not find sources\install.wim or sources\install.esd inside the ISO."
    }

    Write-Host "ISO: $IsoPath"
    Write-Host "Windows image: $installImage"

    Write-Step "Select Windows image edition"
    $images = Get-WindowsImage -ImagePath $installImage
    $selectedImage = $images |
        Where-Object { $_.ImageName -match "Windows 11 Pro" } |
        Select-Object -First 1
    if (-not $selectedImage) {
        $selectedImage = $images | Select-Object -First 1
        Write-Warning "Could not auto-select Windows 11 Pro. Using first image: Index $($selectedImage.ImageIndex), $($selectedImage.ImageName)"
    }
    Write-Host "Selected image: Index $($selectedImage.ImageIndex), $($selectedImage.ImageName)"

    Write-Step "Create and partition VHDX"
    New-VHD -Path $vhdPath -SizeBytes $VhdSizeBytes -Dynamic | Out-Null
    Mount-VHD -Path $vhdPath | Out-Null
    $vhdMounted = $true

    $disk = Get-Disk |
        Where-Object { $_.Location -like "*$([IO.Path]::GetFileName($vhdPath))*" } |
        Select-Object -First 1
    if (-not $disk) {
        throw "Could not find the mounted VHDX disk."
    }

    Initialize-Disk -Number $disk.Number -PartitionStyle GPT

    $efiPartition = New-Partition `
        -DiskNumber $disk.Number `
        -Size 260MB `
        -GptType "{C12A7328-F81F-11D2-BA4B-00A0C93EC93B}" `
        -AssignDriveLetter
    Format-Volume -Partition $efiPartition -FileSystem FAT32 -NewFileSystemLabel "SYSTEM" -Confirm:$false | Out-Null

    New-Partition `
        -DiskNumber $disk.Number `
        -Size 16MB `
        -GptType "{E3C9E316-0B5C-4DB8-817D-F92DF00215AE}" |
        Out-Null

    $windowsPartition = New-Partition -DiskNumber $disk.Number -UseMaximumSize -AssignDriveLetter
    Format-Volume -Partition $windowsPartition -FileSystem NTFS -NewFileSystemLabel "Windows" -Confirm:$false | Out-Null

    $efiDrive = "$($efiPartition.DriveLetter):"
    $windowsDrive = "$($windowsPartition.DriveLetter):"
    Write-Host "EFI partition: $efiDrive"
    Write-Host "Windows partition: $windowsDrive"

    Write-Step "Apply Windows image"
    $applyArgs = @(
        "/Apply-Image",
        "/ImageFile:$installImage",
        "/Index:$($selectedImage.ImageIndex)",
        "/ApplyDir:$windowsDrive\",
        "/CheckIntegrity"
    )
    & dism.exe @applyArgs
    if ($LASTEXITCODE -ne 0) {
        throw "DISM /Apply-Image failed: exit code $LASTEXITCODE"
    }

    Write-Step "Create UEFI boot files"
    & bcdboot.exe "$windowsDrive\Windows" /s $efiDrive /f UEFI
    if ($LASTEXITCODE -ne 0) {
        throw "BCDBoot failed: exit code $LASTEXITCODE"
    }

    Write-Step "Dismount VHDX"
    Dismount-VHD -Path $vhdPath
    $vhdMounted = $false

    Write-Step "Create Hyper-V VM"
    New-VM `
        -Name $VMName `
        -Generation 2 `
        -MemoryStartupBytes $MemoryStartupBytes `
        -VHDPath $vhdPath `
        -Path $VMRoot `
        -SwitchName $SwitchName |
        Out-Null

    Set-VMProcessor -VMName $VMName -Count $ProcessorCount
    Set-VMMemory `
        -VMName $VMName `
        -DynamicMemoryEnabled $true `
        -MinimumBytes $MemoryMinimumBytes `
        -StartupBytes $MemoryStartupBytes `
        -MaximumBytes $MemoryMaximumBytes

    Set-VM -Name $VMName -AutomaticCheckpointsEnabled $false -CheckpointType Disabled
    Set-VMKeyProtector -VMName $VMName -NewLocalKeyProtector
    Enable-VMTPM -VMName $VMName

    $hardDisk = Get-VMHardDiskDrive -VMName $VMName
    Set-VMFirmware `
        -VMName $VMName `
        -EnableSecureBoot On `
        -SecureBootTemplate "MicrosoftWindows" `
        -FirstBootDevice $hardDisk `
        -PauseAfterBootFailure On

    Write-Step "Result"
    Get-VM -Name $VMName |
        Select-Object Name, State, Generation, MemoryStartup, ProcessorCount, AutomaticCheckpointsEnabled, CheckpointType |
        Format-List

    Get-VMFirmware -VMName $VMName |
        Select-Object SecureBoot, SecureBootTemplate, BootOrder |
        Format-List

    if (-not $NoStart) {
        Write-Step "Start VM"
        Start-VM -Name $VMName
        Start-Process vmconnect.exe -ArgumentList "localhost", $VMName
        Write-Host "Check whether VMConnect shows the Windows first-run setup screen."
    } else {
        Write-Host "Skipped VM start because -NoStart was supplied."
    }

    Write-Host ""
    Write-Host "Done. Log: $transcriptPath" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "FAILED: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Log: $transcriptPath" -ForegroundColor Yellow
    throw
} finally {
    if ($vhdMounted -and (Test-Path -LiteralPath $vhdPath)) {
        try {
            Dismount-VHD -Path $vhdPath -ErrorAction SilentlyContinue
        } catch {
            Write-Warning "VHDX cleanup failed: $($_.Exception.Message)"
        }
    }

    if ($isoMountedByScript) {
        try {
            Dismount-DiskImage -ImagePath $IsoPath -ErrorAction SilentlyContinue
        } catch {
            Write-Warning "ISO cleanup failed: $($_.Exception.Message)"
        }
    }

    Stop-Transcript | Out-Null
}
