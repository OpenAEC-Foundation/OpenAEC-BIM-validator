; ==========================================================================
; BIM Validator - Inno Setup Installer Script
; 3BM Bouwkunde - https://3bm.nl
; ==========================================================================

#define MyAppName "BIM Validator"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "3BM Bouwkunde"
#define MyAppURL "https://github.com/OpenAEC/BIM-validator"
#define MyAppExeName "BIMValidator.exe"
#define MyCLIExeName "ifc-validate.exe"

[Setup]
AppId={{7B3A8F2E-4D1C-4E5F-9A8B-1C2D3E4F5A6B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\BIMValidator
DefaultGroupName={#MyAppName}
; Admin rights needed for PATH modification
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=output
OutputBaseFilename=BIMValidator-{#MyAppVersion}-setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; 3BM branding
WizardImageFile=assets\installer_banner.bmp
WizardSmallImageFile=assets\installer_small.bmp
SetupIconFile=tray_icon.ico
UninstallDisplayIcon={app}\server\{#MyAppExeName}
LicenseFile=assets\license.txt
; Minimum Windows 10
MinVersion=10.0
; Show "Launch" checkbox after install
ChangesEnvironment=yes

[Languages]
Name: "dutch"; MessagesFile: "compiler:Languages\Dutch.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Volledige installatie (Web App + CLI)"
Name: "cli"; Description: "Alleen CLI tool"
Name: "custom"; Description: "Aangepaste installatie"; Flags: iscustom

[Components]
Name: "server"; Description: "BIM Validator Web Applicatie (system tray)"; Types: full
Name: "cli"; Description: "ifc-validate CLI tool"; Types: full cli

[Tasks]
Name: "desktopicon"; Description: "Bureaublad snelkoppeling aanmaken"; GroupDescription: "Extra snelkoppelingen:"; Components: server
Name: "autostart"; Description: "BIM Validator starten met Windows"; Components: server
Name: "addtopath"; Description: "ifc-validate toevoegen aan systeem PATH"; Components: cli; Flags: checkedonce

[Files]
; Server + tray app bundle (PyInstaller output)
Source: "dist\BIMValidator\*"; DestDir: "{app}\server"; Components: server; Flags: ignoreversion recursesubdirs createallsubdirs
; CLI bundle (PyInstaller output)
Source: "dist\ifc-validate\*"; DestDir: "{app}\cli"; Components: cli; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start menu — server
Name: "{group}\BIM Validator"; Filename: "{app}\server\{#MyAppExeName}"; Components: server; Comment: "Open BIM Validator in uw browser"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
; Desktop shortcut
Name: "{commondesktop}\BIM Validator"; Filename: "{app}\server\{#MyAppExeName}"; Tasks: desktopicon; Comment: "Open BIM Validator"
; Startup folder (autostart with Windows)
Name: "{commonstartup}\BIM Validator"; Filename: "{app}\server\{#MyAppExeName}"; Tasks: autostart

[Registry]
; App metadata
Root: HKLM; Subkey: "Software\3BM\BIMValidator"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\3BM\BIMValidator"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey

[Run]
; Launch after install
Filename: "{app}\server\{#MyAppExeName}"; Description: "BIM Validator starten"; Flags: nowait postinstall skipifsilent; Components: server

[UninstallRun]
; Clean shutdown before uninstall
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExeName}"; Flags: runhidden; Components: server; RunOnceId: "StopServer"

[Code]
// =========================================================================
// Pascal Script: PATH management for CLI tool
// =========================================================================

const
  EnvironmentKey = 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment';

procedure AddToSystemPath(Dir: string);
var
  OldPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, EnvironmentKey, 'Path', OldPath) then
    OldPath := '';
  // Only add if not already present
  if Pos(Uppercase(Dir), Uppercase(OldPath)) = 0 then
  begin
    if (OldPath <> '') and (OldPath[Length(OldPath)] <> ';') then
      OldPath := OldPath + ';';
    RegWriteStringValue(HKEY_LOCAL_MACHINE, EnvironmentKey, 'Path', OldPath + Dir);
    Log('Added to PATH: ' + Dir);
  end;
end;

procedure RemoveFromSystemPath(Dir: string);
var
  OldPath, NewPath: string;
  P: Integer;
begin
  if RegQueryStringValue(HKEY_LOCAL_MACHINE, EnvironmentKey, 'Path', OldPath) then
  begin
    P := Pos(Uppercase(Dir), Uppercase(OldPath));
    if P > 0 then
    begin
      // Remove the directory and any trailing semicolon
      NewPath := Copy(OldPath, 1, P - 1) + Copy(OldPath, P + Length(Dir), MaxInt);
      // Clean up double semicolons
      while Pos(';;', NewPath) > 0 do
        StringChangeEx(NewPath, ';;', ';', True);
      // Remove leading/trailing semicolons
      if (Length(NewPath) > 0) and (NewPath[1] = ';') then
        Delete(NewPath, 1, 1);
      if (Length(NewPath) > 0) and (NewPath[Length(NewPath)] = ';') then
        Delete(NewPath, Length(NewPath), 1);
      RegWriteStringValue(HKEY_LOCAL_MACHINE, EnvironmentKey, 'Path', NewPath);
      Log('Removed from PATH: ' + Dir);
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('addtopath') then
      AddToSystemPath(ExpandConstant('{app}\cli'));
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemoveFromSystemPath(ExpandConstant('{app}\cli'));
  end;
end;
