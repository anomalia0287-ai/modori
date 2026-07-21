#ifndef AppIdValue
  #error AppIdValue is required
#endif
#ifndef AppNameValue
  #error AppNameValue is required
#endif
#ifndef AppVersionValue
  #error AppVersionValue is required
#endif
#ifndef WindowsFileVersionValue
  #error WindowsFileVersionValue is required
#endif
#ifndef PackageRoot
  #error PackageRoot is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef OutputBaseFilename
  #error OutputBaseFilename is required
#endif
#ifndef AllowCustomDirValue
  #error AllowCustomDirValue is required
#endif
#if Int(AllowCustomDirValue) != 0
  #if Int(AllowCustomDirValue) != 1
    #error AllowCustomDirValue must be 0 or 1
  #endif
#endif

[Setup]
AppId={{{#AppIdValue}}
AppName={#AppNameValue}
AppVersion={#AppVersionValue}
AppVerName={#AppNameValue} {#AppVersionValue}
AppPublisher=Modori Project
DefaultDirName={localappdata}\Programs\Modori
DefaultGroupName=Modori
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no
ChangesAssociations=no
ChangesEnvironment=no
DisableDirPage=yes
DisableProgramGroupPage=yes
UsePreviousAppDir=no
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes
Uninstallable=yes
CreateUninstallRegKey=yes
UninstallDisplayName={#AppNameValue}
UninstallDisplayIcon={app}\Modori\Modori.exe
VersionInfoVersion={#WindowsFileVersionValue}
VersionInfoProductVersion={#WindowsFileVersionValue}
VersionInfoProductName=Modori
VersionInfoDescription=Modori Internal Test Installer
VersionInfoCompany=Modori Project
VersionInfoOriginalFileName={#OutputBaseFilename}.exe

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\Modori"

[Files]
Source: "{#PackageRoot}\*"; DestDir: "{app}\Modori"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppNameValue}"; Filename: "{app}\Modori\Modori.exe"; WorkingDir: "{app}\Modori"
Name: "{autodesktop}\{#AppNameValue}"; Filename: "{app}\Modori\Modori.exe"; WorkingDir: "{app}\Modori"; Tasks: desktopicon

[Run]
Filename: "{app}\Modori\Modori.exe"; Description: "Launch {#AppNameValue}"; Flags: nowait postinstall skipifsilent

[Code]
function ExistingVersionKey: String;
begin
  Result := 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{' +
    '{#AppIdValue}' + '}_is1';
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
#if Int(AllowCustomDirValue) == 0
  if CompareText(WizardDirValue(), ExpandConstant('{localappdata}\Programs\Modori')) <> 0 then
    Result := 'Modori must be installed in ' +
      ExpandConstant('{localappdata}\Programs\Modori') + '.';
#endif
end;

function InitializeSetup: Boolean;
var
  InstalledDisplayVersion: String;
  InstalledPacked: Int64;
  CandidatePacked: Int64;
begin
  Result := True;
  if not RegQueryStringValue(HKCU,
    ExistingVersionKey,
    'DisplayVersion',
    InstalledDisplayVersion
  ) then
    Exit;

  if not StrToVersion(InstalledDisplayVersion + '.0', InstalledPacked) then
  begin
    SuppressibleMsgBox(
      'The installed Modori version is unreadable. Uninstall it before continuing.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
    Exit;
  end;

  if not StrToVersion('{#WindowsFileVersionValue}', CandidatePacked) then
  begin
    SuppressibleMsgBox(
      'The candidate Modori version is invalid.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
    Exit;
  end;

  if ComparePackedVersion(CandidatePacked, InstalledPacked) < 0 then
  begin
    SuppressibleMsgBox(
      'A newer Modori version is installed. Uninstall it before downgrading.',
      mbCriticalError,
      MB_OK,
      IDOK
    );
    Result := False;
  end;
end;
