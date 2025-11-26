<# : batch portion
@echo off & setlocal

set PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%

pushd "%~dp0"

set "p1=%~f0"
set p=%p1:^=%
set p=%p:@=%
set p=%p:&=%
if not "%p1%"=="%p%" goto :badpath

if not "%~nx0"=="config.bat" goto :badname

echo marco | findstr /C:"polo" >nul
if %ERRORLEVEL% EQU 0 goto :wineskip
echo marco | findstr /V /C:"polo" >nul
if %ERRORLEVEL% NEQ 0 goto :wineskip
echo. >nul || goto :wineskip

echo "%~dp0" | findstr /V /C:"%TEMP%" >nul
if %ERRORLEVEL% NEQ 0 goto :temp

set "script_path=%~f0"
set "arg1=%1"

echo "Starting the script... %~f0"
powershell -noprofile "$_PSCommandPath = [Environment]::GetEnvironmentVariable('script_path', 'Process'); iex ((Get-Content -LiteralPath $_PSCommandPath) | out-string)"
if %ERRORLEVEL% EQU 0 goto :EOF

if %ERRORLEVEL% LSS 0 exit /B %ERRORLEVEL%

pause
goto :EOF

:wineskip
echo It looks like you're trying to run this script through Wine - that won't work. If you're on Linux - use setup_linux.sh instead!
pause
goto :EOF

:temp
echo It looks like you're trying to run this script from inside the archive. Make sure you extract the file first.
pause
goto :EOF

:badname
echo Don't rename this script, leave it as "config.bat"!
pause
goto :EOF

:badpath
echo %~dp0
echo You put the Unlocker in a path that will break the setup script. Move it somewhere else, for example "C:\unlocker" or "D:\unlocker". The problematic characters are: @^&^^
pause
goto :EOF
: end batch / begin powershell #>

function Get-Env {
    param (
        [string]$name
    )

    Return [Environment]::GetEnvironmentVariable($name, 'Process')
}

$ErrorActionPreference = 'stop'
Set-Location -LiteralPath (Split-Path -parent $_PSCommandPath)
$FileMissingMessage = ' missing, you didn''t extract all files'
$GameConfigPrefix = 'g_'
$GameConfigSuffix = '.ini'
Clear-Host

function Fail {
    param (
        [string]$message
    )

    Write-Host `n'Fatal error:' -NoNewline -BackgroundColor red -ForegroundColor white
    Warn (' ' + $message)
    Write-Host 'Script path:' $_PSCommandPath
    Write-Host
    Exit 1
}

function Warn {
    param (
        [string]$message
    )

    Write-Host $message -ForegroundColor red
}

function Success {
    param (
        [string]$message
    )

    Write-Host $message -ForegroundColor green
}

function Special {
    param (
        [string]$yellow,
        [string]$suffix
    )

    Write-Host $yellow -NoNewline -ForegroundColor yellow
    Write-Host $suffix
}

function Delete-If-Exists {
    param (
        [string]$path
    )

    If (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

function Create-Config-Directory {
    Try {
        New-Item -Path $appdatadir -ItemType 'Directory' -Force | Out-Null
    }
    Catch {
        Fail 'Could not create the configs folder.'
    }
    Success 'Configs folder created!'
}

function Add-Game-Config {
    $game = 'The Sims 4'
    $configPath = Join-Path 'game_configs' ($GameConfigPrefix + $game + $GameConfigSuffix)

    If (-Not (Test-Path $configPath)) {
        Fail ('Game config ' + $configPath + $FileMissingMessage + '.')
    }

    Create-Config-Directory
    Special $game ' config selected.'
    Try {
        Copy-Item $configPath -Destination $appdatadir -Force
        Success 'Game config copied!'
    }
    Catch {
        Fail 'Could not copy the game config.'
    }

    Try {
        Delete-If-Exists (Join-Path $localappdatadir ($game + '.etag'))
    }
    Catch {}
}

$commondir = 'anadius\EA DLC Unlocker v2'
$appdatadir = Join-Path (Get-Env 'AppData') $commondir
$localappdatadir = Join-Path (Get-Env 'LocalAppData') $commondir

Add-Game-Config
Exit 0