import shutil
import re
import aspose.zip as az
import winreg
from pathlib import Path
from typing import Tuple, List, Optional

TEMP_EXTRACT_DIR = Path("temp_extract")
ARCHIVE_EXTENSIONS = frozenset({'.zip', '.rar', '.7z'})
DLC_PATTERN = re.compile(r'^(EP|GP|SP|FP)(\d{2})$', re.IGNORECASE)


class InstallerManager:
    __slots__ = ('delta_path',)
    
    def __init__(self):
        self.delta_path: Optional[Path] = None
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
    
    def auto_detect_game_path(self) -> Tuple[bool, str]:
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Maxis\The Sims 4") as key:
                install_dir, _ = winreg.QueryValueEx(key, "Install Dir")
            path = Path(install_dir) / "Delta"
            if path.parent.exists():
                self.delta_path = path
                path.mkdir(exist_ok=True)
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
        
        return False, "Game not found"
    
    def set_game_path(self, game_path: str = None) -> bool:
        if game_path is None:
            success, _ = self.auto_detect_game_path()
            return success
        
        if not game_path:
            self.delta_path = None
            return False
        
        path = Path(game_path) / "Delta"
        if path.exists() and path.is_dir():
            self.delta_path = path
            return True
        
        game_path_obj = Path(game_path)
        if game_path_obj.exists() and (game_path_obj / "Game").exists():
            try:
                path.mkdir(exist_ok=True)
                self.delta_path = path
                return True
            except Exception:
                pass
        
        self.delta_path = None
        return False
    
    def _is_dlc_folder(self, folder_name: str) -> bool:
        return bool(DLC_PATTERN.match(folder_name))
    
    def _find_dlc_folders(self, root_path: Path) -> List[Path]:
        dlc_folders = []
        for depth in range(4):
            items = [root_path] if depth == 0 and root_path.exists() else list(root_path.rglob('*' * depth))
            for item in items:
                if item.is_dir() and self._is_dlc_folder(item.name):
                    if any(f.suffix == '.package' for f in item.iterdir() if f.is_file()):
                        dlc_folders.append(item)
        return dlc_folders
    
    def _extract_archive(self, archive_path: Path) -> Tuple[bool, str]:
        self._cleanup_temp()
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
        ext = archive_path.suffix.lower()
        target = str(TEMP_EXTRACT_DIR)
        
        try:
            if ext == '.zip':
                with az.Archive(str(archive_path)) as archive:
                    archive.extract_to_directory(target)
            elif ext == '.rar':
                with az.rar.RarArchive(str(archive_path)) as rar:
                    rar.extract_to_directory(target)
            elif ext == '.7z':
                with az.sevenzip.SevenZipArchive(str(archive_path)) as seven:
                    seven.extract_to_directory(target)
            else:
                return False, f"Unsupported: {ext}"
            return True, "OK"
        except Exception as e:
            return False, str(e)
    
    def _cleanup_temp(self) -> None:
        if TEMP_EXTRACT_DIR.exists():
            shutil.rmtree(TEMP_EXTRACT_DIR, ignore_errors=True)
        TEMP_EXTRACT_DIR.mkdir(exist_ok=True)
    
    def install_file(self, file_path: Path, delete_after: bool = True) -> Tuple[bool, str, List[str]]:
        if not self.delta_path:
            if not self.set_game_path(None):
                return False, "Game path not set", []
        
        if not file_path.exists():
            return False, f"File not found: {file_path}", []
        
        ext = file_path.suffix.lower()
        installed_codes = []
        
        try:
            if ext in ARCHIVE_EXTENSIONS:
                ok, msg = self._extract_archive(file_path)
                if not ok:
                    return False, f"Extraction failed: {msg}", []
                
                dlc_folders = self._find_dlc_folders(TEMP_EXTRACT_DIR)
                if not dlc_folders:
                    self._cleanup_temp()
                    return False, "No DLC folders in archive", []
                
                for dlc_folder in dlc_folders:
                    dest = self.delta_path / dlc_folder.name
                    if dest.exists():
                        shutil.rmtree(dest, ignore_errors=True)
                    shutil.copytree(dlc_folder, dest, dirs_exist_ok=True)
                    installed_codes.append(dlc_folder.name.upper())
                
                self._cleanup_temp()
                
                if delete_after:
                    try:
                        import time
                        import gc
                        gc.collect()
                        time.sleep(0.1)
                        file_path.unlink()
                    except Exception:
                        try:
                            gc.collect()
                            time.sleep(0.5)
                            file_path.unlink()
                        except Exception:
                            pass
                
                return True, f"Installed {len(dlc_folders)} DLC(s)", installed_codes
            else:
                dest = self.delta_path / file_path.name
                shutil.copy2(file_path, dest)
                if delete_after:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
                return True, f"Copied {file_path.name}", []
        except Exception as e:
            self._cleanup_temp()
            return False, str(e), []


installer_mgr = InstallerManager()

