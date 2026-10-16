; MicHP installer (Inno Setup 6.1+ or 7). Called by build.bat.
; One click on Install = MicHP + virtual mic (VB-Cable). VB-Cable is skipped if the PC already has it.
#ifndef AppVersion
  #define AppVersion "1.0"
#endif

[Setup]
AppName=MicHP
AppVersion={#AppVersion}
AppPublisher=MicHP
DefaultDirName={autopf}\MicHP
DefaultGroupName=MicHP
UninstallDisplayIcon={app}\MicHP.exe
SetupIconFile=michp.ico
OutputDir=installer
OutputBaseFilename=MicHP-Setup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
WizardStyle=modern
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Create a Desktop icon"; Flags: checkedonce

[Files]
Source: "dist\MicHP\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\MicHP"; Filename: "{app}\MicHP.exe"; AppUserModelID: "MicHP.App"
Name: "{autodesktop}\MicHP"; Filename: "{app}\MicHP.exe"; AppUserModelID: "MicHP.App"; Tasks: desktopicon

[Run]
Filename: "{app}\MicHP.exe"; Description: "Open MicHP now"; Flags: nowait postinstall skipifsilent

[Code]
const
  CABLE_URL = 'https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip';
  CABLE_SITE = 'https://vb-audio.com/Cable/';

var
  CableChecked: Boolean;
  CableFound: Boolean;
  CableJustInstalled: Boolean;
  CableInfoPage: TOutputMsgWizardPage;

{ Look for VB-Cable in the Windows sound device list (it is called "VB-Audio Virtual Cable"). }
function CableInstalled: Boolean;
var
  Code: Integer;
begin
  if not CableChecked then
  begin
    CableChecked := True;
    CableFound := False;
    if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
      '-NoProfile -NonInteractive -Command "if (Get-CimInstance Win32_SoundDevice | Where-Object { $_.Name -like ''*VB-Audio*Cable*'' -or $_.Name -like ''*CABLE Input*'' }) { exit 0 } else { exit 1 }"',
      '', SW_HIDE, ewWaitUntilTerminated, Code) then
      CableFound := (Code = 0);
    { fallback: the VB-Cable driver files }
    if not CableFound then
      CableFound := FileExists(ExpandConstant('{sys}\drivers\vbaudio_cable64_win10.sys'))
        or FileExists(ExpandConstant('{sys}\drivers\vbaudio_cable64_win7.sys'));
  end;
  Result := CableFound;
end;

procedure InitializeWizard;
begin
  { This page only shows up if VB-Cable is not installed yet (see ShouldSkipPage). }
  CableInfoPage := CreateOutputMsgPage(wpWelcome,
    'One extra component: a virtual mic',
    'Why does MicHP also install VB-Cable?',
    'Windows has no "virtual mic". Discord, games, OBS and Zoom can only pick microphones that are ' +
    'in the Windows device list, so sound from your phone cannot be used directly.' + #13#10 + #13#10 +
    'VB-Cable (free, made by VB-Audio) adds one virtual microphone called "CABLE Output". ' +
    'MicHP sends your phone''s sound into it, and you just pick "CABLE Output" as the microphone in the app you use.' + #13#10 + #13#10 +
    'When you click Install:' + #13#10 +
    '1. MicHP is installed.' + #13#10 +
    '2. VB-Cable is downloaded from its official site and installed (needs internet for a moment). Windows will ask for ' +
    'Administrator permission and "Install this device software?" -> choose Install.' + #13#10 +
    '3. Restart the PC at the end so the virtual mic shows up.' + #13#10 + #13#10 +
    'If installing VB-Cable fails, MicHP is still installed and you are shown how to install it manually.');
end;

{ The info page only shows up if VB-Cable is not installed (and it is not a silent install). }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if (CableInfoPage <> nil) and (PageID = CableInfoPage.ID) then
    Result := CableInstalled or WizardSilent;
end;

function RunPs(const Cmd: String): Boolean;
var
  Code: Integer;
begin
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    '-NoProfile -NonInteractive -Command "' + Cmd + '"', '', SW_HIDE, ewWaitUntilTerminated, Code)
    and (Code = 0);
end;

procedure InstallCable;
var
  Zip, Dir, Setup, Msg: String;
  Code: Integer;
begin
  Zip := ExpandConstant('{tmp}\vbcable.zip');
  Dir := ExpandConstant('{tmp}\vbcable');
  Msg := 'MicHP is installed, but VB-Cable could not be installed automatically.' + #13#10 + #13#10 +
         'Install it manually from ' + CABLE_SITE + ' (download, extract, right-click VBCABLE_Setup_x64.exe -> Run as administrator), then restart the PC.';
  try
    { empty hash = no hash check (the file is always fetched from vb-audio.com) }
    DownloadTemporaryFile(CABLE_URL, 'vbcable.zip', '', nil);
  except
    MsgBox('The VB-Cable download failed (' + GetExceptionMessage + ').' + #13#10 + #13#10 + Msg, mbInformation, MB_OK);
    Exit;
  end;
  if not RunPs('Expand-Archive -LiteralPath ''' + Zip + ''' -DestinationPath ''' + Dir + ''' -Force') then
  begin
    MsgBox('The VB-Cable files could not be extracted.' + #13#10 + #13#10 + Msg, mbInformation, MB_OK);
    Exit;
  end;
  if IsWin64 then Setup := Dir + '\VBCABLE_Setup_x64.exe' else Setup := Dir + '\VBCABLE_Setup.exe';
  if not FileExists(Setup) then
  begin
    MsgBox('The VB-Cable installer was not found in the download.' + #13#10 + #13#10 + Msg, mbInformation, MB_OK);
    Exit;
  end;
  { "runas" = ask for Administrator permission (the driver installer needs it). -i -h = install, no main window. }
  if ShellExec('runas', Setup, '-i -h', Dir, SW_SHOW, ewWaitUntilTerminated, Code) and (Code = 0) then
    CableJustInstalled := True
  else
    MsgBox('The VB-Cable installation was cancelled or failed.' + #13#10 + #13#10 + Msg, mbInformation, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssPostInstall) and (not WizardSilent) and (not CableInstalled) then
    InstallCable;
end;

{ Ask for a restart at the end if VB-Cable was just installed. }
function NeedRestart: Boolean;
begin
  Result := CableJustInstalled;
end;

{ Summary on the "Ready to Install" page: show that VB-Cable is installed too. }
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
begin
  Result := MemoDirInfo;
  if MemoTasksInfo <> '' then
    Result := Result + NewLine + NewLine + MemoTasksInfo;
  Result := Result + NewLine + NewLine + 'Virtual mic:' + NewLine;
  if CableInstalled then
    Result := Result + Space + 'VB-Cable is already installed, no need to install it again.'
  else
    Result := Result + Space + 'VB-Cable will be downloaded and installed (needs internet + Administrator permission).';
end;
