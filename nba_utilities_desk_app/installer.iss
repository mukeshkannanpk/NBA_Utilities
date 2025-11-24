; NBA Utilities Installer Script for Inno Setup
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "NBA Utilities"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NBA"
#define MyAppExeName "NBA_Utilities.exe"

[Setup]
AppId={{A1B2C3D4-5E6F-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=NBA_Utilities_Package\LICENSE.txt
InfoBeforeFile=NBA_Utilities_Package\README.txt
OutputDir=Installer
OutputBaseFilename=NBA_Utilities_Setup_v{#MyAppVersion}
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; FIXED: Changed from x64 to x64compatible
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; FIXED: Changed from admin to lowest (per-user install)
PrivilegesRequired=lowest
; FIXED: Removed this line as it's deprecated
; PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
; FIXED: Add user mode settings
UsePreviousAppDir=yes
UsePreviousGroup=yes
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Main application
Source: "NBA_Utilities_Package\NBA_Utilities.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "NBA_Utilities_Package\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up user data on uninstall (optional - remove if you want to keep user data)
Type: filesandordirs; Name: "{localappdata}\NBA\NBA_Utilities"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create user data directory
    ForceDirectories(ExpandConstant('{localappdata}\NBA\NBA_Utilities'));
  end;
end;