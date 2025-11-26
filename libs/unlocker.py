import subprocess
from pathlib import Path
from typing import Tuple

from libs.locale import locale_mgr

UNLOCKER_DIR = Path("unlocker")
CONFIG_INI = UNLOCKER_DIR / "config.ini"
INSTALL_BAT = UNLOCKER_DIR / "install.bat"
UNINSTALL_BAT = UNLOCKER_DIR / "uninstall.bat"
GAME_CONFIG_BAT = UNLOCKER_DIR / "config.bat"
CHECK_STATUS_BAT = UNLOCKER_DIR / "check.bat"


class UnlockerManager:
    __slots__ = ()
    
    def __init__(self):
        UNLOCKER_DIR.mkdir(exist_ok=True)
    
    def _run_check(self, arg: str) -> bool:
        if not CHECK_STATUS_BAT.exists():
            return False
        
        try:
            result = subprocess.run(
                [str(CHECK_STATUS_BAT), arg],
                shell=True,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_unlocker_installed(self) -> bool:
        return self._run_check('unlocker')
    
    def is_sims4_installed(self) -> bool:
        return self._run_check('game:g_The Sims 4.ini')
    
    def is_config_installed(self) -> bool:
        return self._run_check('config')
    
    def _run_bat(self, bat_file: Path) -> Tuple[bool, str]:
        if not bat_file.exists():
            return False, f"{locale_mgr.t('file_not_exists')}: {bat_file}"
        
        try:
            result = subprocess.run(
                [str(bat_file)],
                shell=True,
                capture_output=True,
                text=True
            )
            return result.returncode == 0, result.stderr
        except Exception as e:
            return False, f"{locale_mgr.t('bat_run_error')}: {e}"
    
    def install_with_sims4(self) -> Tuple[bool, str]:
        ok, err = self._run_bat(INSTALL_BAT)
        if not ok:
            return False, f"{locale_mgr.t('unlocker_install_error')}: {err}"
        
        if not GAME_CONFIG_BAT.exists():
            return False, f"{locale_mgr.t('file_not_exists')}: {GAME_CONFIG_BAT}"
        
        ok, err = self._run_bat(GAME_CONFIG_BAT)
        if not ok:
            return False, f"{locale_mgr.t('unlocker_installed_sims_error')}: {err}"
        
        return True, locale_mgr.t('dlc_unlocker_installed')
    
    def uninstall_unlocker(self) -> Tuple[bool, str]:
        ok, err = self._run_bat(UNINSTALL_BAT)
        if ok:
            return True, locale_mgr.t('dlc_unlocker_uninstalled')
        return False, f"{locale_mgr.t('uninstall_error')}: {err}"
    
    def is_config_available(self) -> bool:
        return CONFIG_INI.exists()


unlocker_mgr = UnlockerManager()