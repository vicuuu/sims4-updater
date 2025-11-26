<# : batch portion
@echo off & setlocal

set PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%

pushd "%~dp0"

set "p1=%~f0"
set p=%p1:^=%
set p=%p:@=%
set p=%p:&=%
if not "%p1%"=="%p%" goto :badpath

if not "%~nx0"=="uninstall.bat" goto :badname

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
echo Don't rename this script, leave it as "uninstall.bat"!
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

$arg1 = Get-Env 'arg1'

$ErrorActionPreference = 'stop'
Set-Location -LiteralPath (Split-Path -parent $_PSCommandPath)
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

function Force-Stop-Clients {
    If ($client -Eq 'origin') {
        $wildcard = 'Origin*'
    }
    Else {
        $wildcard = 'EA*'
    }
    Stop-Process -Force -Name $wildcard
    Wait-Process -Name $wildcard -Timeout 10
}

function Delete-Folder-Recursively {
    param (
        [string]$directory
    )

    If (Test-Path -LiteralPath $directory) {
        Get-ChildItem -LiteralPath $directory -Force -Recurse | Remove-Item -Force
        Remove-Item -LiteralPath $directory -Force
    }
}

function Delete-Folder-If-Empty {
    param (
        [string]$directory
    )

    If ((Test-Path -LiteralPath $directory) -And ((Get-ChildItem -LiteralPath $directory).Count -Eq 0)) {
        Remove-Item -LiteralPath $directory -Force
    }
}

function Get-Client-Path-From-Registry {
    param (
        [string]$RegistryPath
    )

    $path = (Get-ItemProperty -Path ('Registry::HKEY_LOCAL_MACHINE\SOFTWARE\' + $RegistryPath) -Name ClientPath).ClientPath
    Return (Resolve-Path -LiteralPath (Join-Path $path '..'))
}

function Is-Admin {
    Return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Is-Special-Admin {
    Return ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).Identity.User -like 'S-1-5-21-*-500'
}

function Delete-If-Exists {
    param (
        [string]$path
    )

    If (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
    }
}

function Common-Setup-Real {
    param (
        [string]$action
    )

    If (-Not (Is-Admin)) {
        Special 'Requesting administrator rights...'
        # with "-Wait" it throws an error on Win 7
        $process = Start-Process -FilePath uninstall.bat -Verb RunAs -WorkingDirectory . -ArgumentList $action -PassThru
        If (!($process.Id)) {
            Fail 'Failed to get administrator rights.'
        }
        while (!($process.HasExited)) {
            Start-Sleep -Milliseconds 200
        }
        # you have to do it like that without "-Wait"...
        Return $process.GetType().GetField('exitCode', 'NonPublic, Instance').GetValue($process)
    }

    Try {
        Force-Stop-Clients
        Start-Sleep -Seconds 1
        If ($action -Eq 'uninstall') {
            Delete-If-Exists $dstdll
            Delete-If-Exists $dstdll2
            $ErrorActionPreference = 'silentlycontinue'
            & schtasks /Delete /TN copy_dlc_unlocker /F 2>&1 | Out-Null
            $ErrorActionPreference = 'stop'
            Return 0
        }
        Else {
            Return -1
        }
    }
    Catch {
        $ErrorActionPreference = 'stop'
        Write-Host $_
        $tmp = Read-Host -Prompt "Press enter to exit"
        Return -1
    }
}

function Common-Setup {
    param (
        [string]$action
    )

    $result = Common-Setup-Real $action
    If ($result -Ne 0) {
        Fail ('An error occured. Could not ' + $action + ' the Unlocker.')
    }
}

function Uninstall-Unlocker {
    Write-Host 'Uninstalling...'

    Try {
        Delete-Folder-Recursively $appdatadir
        Delete-Folder-If-Empty (Join-Path $appdatadir '..')
        Success 'Configs folder deleted!'
    }
    Catch {
        Warn 'Could not delete the configs folder.'
    }

    Common-Setup 'uninstall'
    Success 'DLC Unlocker uninstalled!'

    Try {
        Delete-Folder-Recursively $localappdatadir
        Delete-Folder-If-Empty (Join-Path $localappdatadir '..')
        Success 'Logs folder deleted!'
    }
    Catch {
        Warn 'Could not delete the logs folder.'
    }
}

$client = 'ea_app'
$client_name = 'EA app'
Try {
    $client_path = Get-Client-Path-From-Registry 'Electronic Arts\EA Desktop'
}
Catch {
    $client = 'origin'
    $client_name = 'Origin'
    Try {
        $client_path = Get-Client-Path-From-Registry 'WOW6432Node\Origin'
    }
    Catch {
        Try {
            $client_path = Get-Client-Path-From-Registry 'Origin'
        }
        Catch {
            Fail 'EA app/Origin not found, reinstall one of them.'
        }
    }
}

$dstdll = Join-Path $client_path 'version.dll'
$stageddir = Join-Path (Join-Path -Resolve $client_path '..') 'StagedEADesktop\EA Desktop'
$dstdll2 = Join-Path $stageddir 'version.dll'

$commondir = 'anadius\EA DLC Unlocker v2'
$appdatadir = Join-Path (Get-Env 'AppData') $commondir
$localappdatadir = Join-Path (Get-Env 'LocalAppData') $commondir

If ($arg1 -Eq 'uninstall') {
    Exit (Common-Setup-Real $arg1)
}

If (Is-Admin) {
    If (Is-Special-Admin) {
        Warn "DON'T run this script as administrator. It's not necessary.`nThis script will ask for administrator rights when needed.`nIf you run this script by double clicking and still see this error - you use a special Administrator account.`nIf you get any problems - that's probably the reason why. Don't report it."
    }
    Else {
        Fail "DON'T run this script as administrator. It's not necessary.`nThis script will ask for administrator rights when needed.`nIf you run this script by double clicking and still see this error - you probably have UAC disabled. So enable it."
    }
}

Uninstall-Unlocker
Exit 0