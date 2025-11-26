<# : batch portion
@echo off & setlocal

set PATH=%SystemRoot%\System32;%SystemRoot%;%SystemRoot%\System32\WindowsPowerShell\v1.0;%PATH%

pushd "%~dp0"

set "script_path=%~f0"
set "arg1=%~1"

powershell -noprofile "$_PSCommandPath = [Environment]::GetEnvironmentVariable('script_path', 'Process'); $arg1 = [Environment]::GetEnvironmentVariable('arg1', 'Process'); iex ((Get-Content -LiteralPath $_PSCommandPath) | out-string)"
exit /B %ERRORLEVEL%

: end batch / begin powershell #>

function Get-Env {
    param (
        [string]$name
    )

    Return [Environment]::GetEnvironmentVariable($name, 'Process')
}

$arg1 = Get-Env 'arg1'
$ErrorActionPreference = 'stop'

$commondir = 'anadius\EA DLC Unlocker v2'
$appdatadir = Join-Path (Get-Env 'AppData') $commondir

function Get-Client-Path-From-Registry {
    param (
        [string]$RegistryPath
    )

    Try {
        $path = (Get-ItemProperty -Path ('Registry::HKEY_LOCAL_MACHINE\SOFTWARE\' + $RegistryPath) -Name ClientPath).ClientPath
        Return (Resolve-Path -LiteralPath (Join-Path $path '..'))
    }
    Catch {
        Return $null
    }
}

function Get-Client-Path {
    # Próbuj EA Desktop
    $client_path = Get-Client-Path-From-Registry 'Electronic Arts\EA Desktop'
    If ($client_path) {
        Return $client_path
    }
    
    # Próbuj Origin 64-bit
    $client_path = Get-Client-Path-From-Registry 'WOW6432Node\Origin'
    If ($client_path) {
        Return $client_path
    }
    
    # Próbuj Origin 32-bit
    $client_path = Get-Client-Path-From-Registry 'Origin'
    If ($client_path) {
        Return $client_path
    }
    
    Return $null
}

function Check-Unlocker-Installed {
    $client_path = Get-Client-Path
    If (-Not $client_path) {
        Return 1  # Nie znaleziono klienta
    }
    
    $dllPath = Join-Path $client_path 'version.dll'
    If (Test-Path -LiteralPath $dllPath) {
        Return 0  # Zainstalowany
    }
    Return 1  # Nie zainstalowany
}

function Check-Game-Config-Installed {
    param (
        [string]$configName
    )
    
    $configPath = Join-Path $appdatadir $configName
    If (Test-Path -LiteralPath $configPath) {
        Return 0  # Zainstalowany
    }
    Return 1  # Nie zainstalowany
}

If ($arg1 -Eq 'unlocker') {
    Exit (Check-Unlocker-Installed)
}
ElseIf ($arg1 -Like 'game:*') {
    $gameName = $arg1.Substring(5)
    Exit (Check-Game-Config-Installed $gameName)
}
Else {
    Exit 2  # Nieprawidłowy argument
}