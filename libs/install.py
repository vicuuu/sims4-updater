import aspose.zip as az
import shutil
from pathlib import Path
from typing import Tuple, List, Optional
import winreg

DOWNLOAD_DIR = Path("downloads")
TEMP_EXTRACT_DIR = Path("temp_extract")

ARCHIVE_EXTENSIONS = frozenset({'.zip', '.rar', '.7z'})

class InstallerManager:
    __slots__ = ('delta_path',)
    
    def __init__(self):
        self.delta_path: Optional[Path] = None
        DOWNLOAD_DIR.mkdir(exist_ok=True)
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
    
    def get_sims4_path(self) -> Tuple[bool, str]:
        from libs.locale import locale_mgr
        
        if self.delta_path and self.delta_path.exists():
            return True, str(self.delta_path.parent)
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Maxis\The Sims 4") as key:
                install_dir, _ = winreg.QueryValueEx(key, "Install Dir")
            self.delta_path = Path(install_dir) / "Delta"
            self.delta_path.mkdir(exist_ok=True)
            return True, install_dir
        except OSError:
            pass
        
        search_paths = (
            Path("C:/Program Files/EA Games/The Sims 4"),
            Path("C:/Program Files (x86)/EA Games/The Sims 4"),
            Path("C:/Program Files/Origin Games/The Sims 4"),
            Path("C:/Program Files (x86)/Origin Games/The Sims 4"),
        )
        
        for path in search_paths:
            if path.exists():
                self.delta_path = path / "Delta"
                self.delta_path.mkdir(exist_ok=True)
                return True, str(path)
        
        return False, locale_mgr.t("game_not_found")
    
    def get_all_items(self) -> List[Path]:
        items = []
        for ext in ARCHIVE_EXTENSIONS:
            items.extend(DOWNLOAD_DIR.rglob(f"*{ext}"))
        return sorted(items, key=lambda p: p.name.lower())
    
    def _extract_archive(self, archive_path: Path) -> Tuple[bool, str]:
        from libs.locale import locale_mgr
        
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
        ext = archive_path.suffix.lower()
        target = str(TEMP_EXTRACT_DIR)
        
        try:
            if ext == '.zip':
                az.Archive(str(archive_path)).extract_to_directory(target)
            elif ext == '.rar':
                with az.rar.RarArchive(str(archive_path)) as rar:
                    rar.extract_to_directory(target)
            elif ext == '.7z':
                with az.sevenzip.SevenZipArchive(str(archive_path)) as seven:
                    seven.extract_to_directory(target)
            else:
                return False, f"{locale_mgr.t('unsupported_format')}: {ext}"
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    def _ensure_delta_path(self) -> Tuple[bool, str]:
        from libs.locale import locale_mgr
        
        if not self.delta_path:
            ok, msg = self.get_sims4_path()
            if not ok:
                return False, locale_mgr.t("game_not_found")
        return True, ""
    
    def _cleanup_temp(self) -> None:
        shutil.rmtree(TEMP_EXTRACT_DIR, ignore_errors=True)
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
    
    def _safe_delete(self, path: Path) -> None:
        try:
            path.unlink()
        except OSError:
            pass
    
    def install_item(self, item_path: Path) -> Tuple[bool, str]:
        from libs.locale import locale_mgr
        
        ok, msg = self._ensure_delta_path()
        if not ok:
            return False, msg
        
        ext = item_path.suffix.lower()
        
        try:
            if ext in ARCHIVE_EXTENSIONS:
                ok, msg = self._extract_archive(item_path)
                if not ok:
                    return False, msg
                
                count = 0
                for item in TEMP_EXTRACT_DIR.rglob("*"):
                    if item.is_file():
                        dest = self.delta_path / item.relative_to(TEMP_EXTRACT_DIR)
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
                        count += 1
                
                self._cleanup_temp()
                self._safe_delete(item_path)
                return True, f"{locale_mgr.t('installed')} {count} {locale_mgr.t('files')}"
            else:
                dest = self.delta_path / item_path.name
                shutil.copy2(item_path, dest)
                self._safe_delete(item_path)
                return True, f"OK: {item_path.name}"
                
        except Exception as e:
            return False, str(e)
    
    def install_all_items(self) -> Tuple[bool, str, int]:
        from libs.locale import locale_mgr
        
        items = self.get_all_items()
        if not items:
            return False, locale_mgr.t("no_files_to_install"), 0
        
        ok_count = 0
        failures = []
        
        for item in items:
            success, msg = self.install_item(item)
            if success:
                ok_count += 1
            else:
                failures.append(f"{item.name}: {msg}")
        
        if failures:
            return False, f"OK: {ok_count}/{len(items)}\n" + "\n".join(failures), ok_count
        return True, f"OK: {ok_count}", ok_count


installer_mgr = InstallerManager()