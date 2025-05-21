@echo off
setlocal enabledelayedexpansion

echo ========================================================================
echo Discord Audio Bot Setup for Windows
echo ========================================================================
echo.

:: Check for administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please right-click on the script and select "Run as administrator".
    pause
    exit /b 1
)

:: Set up variables
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
cd /d "%SCRIPT_DIR%"

echo Working directory: %SCRIPT_DIR%
echo.

:: Check for Python
echo Checking for Python installation...
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo Python not found. Installing Python...
    call :install_python
) else (
    echo Python is already installed.
    python --version
)

:: Check for Git
echo.
echo Checking for Git installation...
where git >nul 2>&1
if %errorLevel% neq 0 (
    echo Git not found. Installing Git...
    call :install_git
) else (
    echo Git is already installed.
    git --version
)

:: Check for FFmpeg
echo.
echo Checking for FFmpeg installation...
where ffmpeg >nul 2>&1
if %errorLevel% neq 0 (
    echo FFmpeg not found. Installing FFmpeg...
    call :install_ffmpeg
) else (
    echo FFmpeg is already installed.
    ffmpeg -version | findstr "version"
)

:: Run the Python setup script
echo.
echo Running Python setup script...
python "%SCRIPT_DIR%\setup.py"

echo.
echo ========================================================================
echo Setup complete!
echo ========================================================================
echo.
echo To run the bot:
echo 1. Activate the virtual environment: .\venv\Scripts\activate
echo 2. Run the bot: python bot.py
echo.
echo Remember to edit the .env file with your Discord bot token and other API keys.
echo.
pause
exit /b 0

:: Functions

:install_python
echo Downloading Python installer...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.0/python-3.11.0-amd64.exe' -OutFile '%TEMP%\python-installer.exe'}"
if %errorLevel% neq 0 (
    echo Failed to download Python installer.
    exit /b 1
)

echo Installing Python...
%TEMP%\python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorLevel% neq 0 (
    echo Failed to install Python.
    exit /b 1
)

:: Wait for Python to be available in PATH
echo Waiting for Python installation to complete...
timeout /t 10 /nobreak >nul

:: Verify Python installation
where python >nul 2>&1
if %errorLevel% neq 0 (
    echo Python installation failed or PATH not updated.
    echo Please install Python manually from https://www.python.org/downloads/windows/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo Python installed successfully.
python --version
exit /b 0

:install_git
echo Downloading Git installer...
powershell -Command "& {Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.40.0.windows.1/Git-2.40.0-64-bit.exe' -OutFile '%TEMP%\git-installer.exe'}"
if %errorLevel% neq 0 (
    echo Failed to download Git installer.
    exit /b 1
)

echo Installing Git...
%TEMP%\git-installer.exe /VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS
if %errorLevel% neq 0 (
    echo Failed to install Git.
    exit /b 1
)

:: Wait for Git to be available in PATH
echo Waiting for Git installation to complete...
timeout /t 10 /nobreak >nul

:: Verify Git installation
where git >nul 2>&1
if %errorLevel% neq 0 (
    echo Git installation failed or PATH not updated.
    echo Please install Git manually from https://git-scm.com/download/win
    pause
    exit /b 1
)

echo Git installed successfully.
git --version
exit /b 0

:install_ffmpeg
echo Downloading 7-Zip...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.7-zip.org/a/7z2201-x64.exe' -OutFile '%TEMP%\7z-installer.exe'}"
if %errorLevel% neq 0 (
    echo Failed to download 7-Zip installer.
    exit /b 1
)

echo Installing 7-Zip...
%TEMP%\7z-installer.exe /S
if %errorLevel% neq 0 (
    echo Failed to install 7-Zip.
    exit /b 1
)

:: Wait for 7-Zip to install
timeout /t 5 /nobreak >nul

echo Downloading FFmpeg...
powershell -Command "& {Invoke-WebRequest -Uri 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-full.7z' -OutFile '%TEMP%\ffmpeg.7z'}"
if %errorLevel% neq 0 (
    echo Failed to download FFmpeg.
    exit /b 1
)

echo Extracting FFmpeg...
"%ProgramFiles%\7-Zip\7z.exe" x "%TEMP%\ffmpeg.7z" -o"%TEMP%\ffmpeg" -y
if %errorLevel% neq 0 (
    echo Failed to extract FFmpeg.
    exit /b 1
)

:: Find the extracted directory (it includes version in the name)
for /d %%i in ("%TEMP%\ffmpeg\ffmpeg-*") do set "FFMPEG_DIR=%%i"

:: Create FFmpeg directory in Program Files
if not exist "%ProgramFiles%\FFmpeg" mkdir "%ProgramFiles%\FFmpeg"

:: Copy FFmpeg files
echo Installing FFmpeg to %ProgramFiles%\FFmpeg...
xcopy "%FFMPEG_DIR%\bin\*" "%ProgramFiles%\FFmpeg\" /E /Y
if %errorLevel% neq 0 (
    echo Failed to copy FFmpeg files.
    exit /b 1
)

:: Add FFmpeg to PATH
echo Adding FFmpeg to PATH...
setx PATH "%PATH%;%ProgramFiles%\FFmpeg" /M
if %errorLevel% neq 0 (
    echo Failed to add FFmpeg to PATH.
    exit /b 1
)

:: Refresh environment variables
call RefreshEnv.cmd >nul 2>&1

:: Verify FFmpeg installation
where ffmpeg >nul 2>&1
if %errorLevel% neq 0 (
    echo FFmpeg installation failed or PATH not updated.
    echo Please install FFmpeg manually and add it to your PATH.
    echo See instructions at: https://www.gyan.dev/ffmpeg/builds/
    pause
    exit /b 1
)

echo FFmpeg installed successfully.
ffmpeg -version | findstr "version"
exit /b 0
