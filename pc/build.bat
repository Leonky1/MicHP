@echo off
setlocal
cd /d "%~dp0"
echo === MicHP: building the app (.exe) ===

rem Pick Python 3.10 - 3.13 (pywebview needs Python 3.8+, so Python 3.7 does NOT work).
set "PY="
for %%V in (3.12 3.13 3.11 3.10) do if not defined PY (py -%%V -c "import sys" >nul 2>nul && set "PY=py -%%V")
if defined PY goto pyok
where python >nul 2>nul || goto nopy
python -c "import sys; sys.exit(0 if sys.version_info>=(3,10) else 1)" >nul 2>nul || goto nopy
set "PY=python"
:pyok
echo Using Python: %PY%
%PY% --version

rem Clean virtual environment: only the MicHP packages get bundled (not all of Anaconda).
if not exist "%~dp0.venv-build\Scripts\python.exe" %PY% -m venv "%~dp0.venv-build"
if not exist "%~dp0.venv-build\Scripts\python.exe" goto venvfail
set "VPY=%~dp0.venv-build\Scripts\python.exe"

"%VPY%" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto pipfail

"%VPY%" -m PyInstaller --noconfirm --clean --windowed --name MicHP ^
  --icon michp.ico ^
  --add-data "michp_pc\static;michp_pc\static" --add-data "michp.ico;." ^
  --collect-all sounddevice --collect-all _sounddevice_data ^
  --collect-all webview --collect-all clr_loader --collect-all pythonnet ^
  michp_app.py
if errorlevel 1 goto buildfail

echo.
rem Look for Inno Setup (version 6 or 7). The last one set wins, so 7 is preferred.
set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do set "ISCC=%%I"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 7\ISCC.exe"

if not defined ISCC goto noinno

echo Using Inno Setup: %ISCC%
"%ISCC%" installer.iss
if errorlevel 1 goto innofail
echo.
echo DONE. Installer: %~dp0installer\MicHP-Setup.exe
echo Double-click that file to install, then open "MicHP" from the Start Menu.
goto end

:innofail
echo Could not build the installer.
goto end

:noinno
echo Inno Setup was not found, so the installer .exe was not built.
echo The app can still be used directly: %~dp0dist\MicHP\MicHP.exe
echo Install Inno Setup 6 or 7 ^(free, jrsoftware.org^) and run build.bat again.
goto end

:nopy
echo Python 3.10 or newer was not found ^(the one detected is too old, e.g. 3.7^).
echo Install Python 3.12 from python.org ^(tick "Add python.exe to PATH"^), then run build.bat again.
goto end

:venvfail
echo Could not create the virtual environment ^(.venv-build^).
goto end

:pipfail
echo Could not install the packages.
goto end

:buildfail
echo Build failed.

:end
pause
