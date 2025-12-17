import winreg
import shutil
import os
import sys
import subprocess
import ctypes
from pathlib import Path
from typing import Tuple, Optional


def get_appdata_dir(roaming: bool = True) -> Optional[Path]:
    if sys.platform != "win32":
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders")
        dir_path, _ = winreg.QueryValueEx(key, "AppData" if roaming else "Local AppData")
        winreg.CloseKey(key)
        return Path(dir_path).resolve(strict=False)
    except Exception:
        env_path = os.getenv('APPDATA' if roaming else 'LOCALAPPDATA')
        if env_path:
            return Path(env_path)
        userprofile = os.getenv('USERPROFILE')
        if userprofile:
            return Path(userprofile) / 'AppData' / ('Roaming' if roaming else 'Local')
        return None


class UnlockerManager:
    __slots__ = ('unlocker_dir', 'appdata_dir', 'localappdata_dir')
    
    def __init__(self, unlocker_dir: Path):
        self.unlocker_dir = unlocker_dir
        appdata = get_appdata_dir(roaming=True)
        localappdata = get_appdata_dir(roaming=False)
        self.appdata_dir = appdata / 'anadius' / 'EA DLC Unlocker v2' if appdata else None
        self.localappdata_dir = localappdata / 'anadius' / 'EA DLC Unlocker v2' if localappdata else None
    
    def _get_client_path_from_registry(self, registry_path: str) -> Optional[Path]:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, f"SOFTWARE\\{registry_path}")
            client_path, _ = winreg.QueryValueEx(key, "ClientPath")
            winreg.CloseKey(key)
            return Path(client_path).parent
        except Exception:
            return None
    
    def get_client_info(self) -> Tuple[Optional[str], Optional[Path]]:
        client_path = self._get_client_path_from_registry('Electronic Arts\\EA Desktop')
        if client_path:
            return 'ea_app', client_path
        
        client_path = self._get_client_path_from_registry('WOW6432Node\\Origin')
        if client_path:
            return 'origin', client_path
        
        client_path = self._get_client_path_from_registry('Origin')
        if client_path:
            return 'origin', client_path
        
        return None, None
    
    def is_unlocker_installed(self) -> bool:
        client_type, client_path = self.get_client_info()
        if not client_path:
            return False
        
        dll_installed = (client_path / 'version.dll').exists()
        
        config_installed = False
        if self.appdata_dir:
            config_installed = (self.appdata_dir / 'config.ini').exists() and (self.appdata_dir / 'g_The Sims 4.ini').exists()
        
        return dll_installed and config_installed
    
    def get_unlocker_status(self) -> dict:
        client_type, client_path = self.get_client_info()
        if not client_path:
            return {'installed': False, 'dll': False, 'config': False, 'game_config': False}
        
        dll_installed = (client_path / 'version.dll').exists()
        config_installed = False
        game_config_installed = False
        
        if self.appdata_dir:
            config_installed = (self.appdata_dir / 'config.ini').exists()
            game_config_installed = (self.appdata_dir / 'g_The Sims 4.ini').exists()
        
        return {
            'installed': dll_installed and config_installed and game_config_installed,
            'dll': dll_installed,
            'config': config_installed,
            'game_config': game_config_installed
        }
    
    def _kill_client_processes(self, client_type: str) -> None:
        process_name = 'Origin.exe' if client_type == 'origin' else 'EADesktop.exe'
        try:
            subprocess.run(['taskkill', '/F', '/IM', process_name], capture_output=True, timeout=10)
        except Exception:
            pass
    
    def _create_folder_and_copy_as_admin(self, src: Path, dst: Path) -> bool:
        try:
            import tempfile
            import uuid
            marker_file = Path(tempfile.gettempdir()) / f"appdata_copy_success_{uuid.uuid4().hex}.tmp"
            folder_path = dst.parent
            
            vbs_content = f'''Set objFSO = CreateObject("Scripting.FileSystemObject")
            On Error Resume Next
            CreateFolderRecursive "{folder_path}"
            objFSO.CopyFile "{src}", "{dst}", True
            If Err.Number = 0 Then
                objFSO.CreateTextFile "{marker_file}", True
            End If

            Sub CreateFolderRecursive(strPath)
                Dim objFSO, strParent
                Set objFSO = CreateObject("Scripting.FileSystemObject")
                strParent = objFSO.GetParentFolderName(strPath)
                If strParent <> "" Then
                    If Not objFSO.FolderExists(strParent) Then
                        CreateFolderRecursive strParent
                    End If
                End If
                If Not objFSO.FolderExists(strPath) Then
                    objFSO.CreateFolder strPath
                End If
            End Sub
            '''
            
            vbs_file = Path(tempfile.gettempdir()) / f"appdata_copy_{uuid.uuid4().hex}.vbs"
            with open(vbs_file, 'w') as f:
                f.write(vbs_content)
            
            ret = ctypes.windll.shell32.ShellExecuteW(None, "open", "wscript.exe", f'"{vbs_file}"', None, 0)
            if ret <= 32:
                try:
                    vbs_file.unlink()
                except:
                    pass
                return False
            
            import time
            max_wait = 10
            waited = 0
            while waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                if marker_file.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
                if dst.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
            
            try:
                vbs_file.unlink()
                if marker_file.exists():
                    marker_file.unlink()
            except:
                pass
            return False
        except Exception:
            return False
    
    def _copy_file_as_admin(self, src: Path, dst: Path) -> bool:
        try:
            import tempfile
            import uuid
            marker_file = Path(tempfile.gettempdir()) / f"copy_success_{uuid.uuid4().hex}.tmp"
            
            vbs_content = f'''Set objFSO = CreateObject("Scripting.FileSystemObject")
            On Error Resume Next
            objFSO.CopyFile "{src}", "{dst}", True
            If Err.Number = 0 Then
                objFSO.CreateTextFile "{marker_file}", True
            End If
            '''
            
            vbs_file = Path(tempfile.gettempdir()) / f"admin_copy_{uuid.uuid4().hex}.vbs"
            with open(vbs_file, 'w') as f:
                f.write(vbs_content)
            
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "wscript.exe", f'"{vbs_file}"', None, 0)
            if ret <= 32:
                try:
                    vbs_file.unlink()
                except:
                    pass
                return False
            
            import time
            max_wait = 10
            waited = 0
            while waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                if marker_file.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
                if dst.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
            
            try:
                vbs_file.unlink()
                if marker_file.exists():
                    marker_file.unlink()
            except:
                pass
            return False
        except Exception:
            return False
    
    def install_unlocker(self, locale) -> Tuple[bool, str]:
        client_type, client_path = self.get_client_info()
        if not client_path:
            return False, locale.t("ea_not_found")
        
        src_dll = self.unlocker_dir / client_type / 'version.dll'
        if not src_dll.exists():
            return False, locale.t("dll_not_found", src_dll)
        
        src_config = self.unlocker_dir / 'config.ini'
        if not src_config.exists():
            return False, locale.t("config_not_found", src_config)
        
        src_game_config = self.unlocker_dir / 'game_configs' / 'g_The Sims 4.ini'
        if not src_game_config.exists():
            return False, locale.t("game_config_not_found", src_game_config)
        
        try:
            self._kill_client_processes(client_type)
            
            if not self.appdata_dir:
                return False, locale.t("appdata_unavailable")
            
            dst_config = self.appdata_dir / 'config.ini'
            if not self._create_folder_and_copy_as_admin(src_config, dst_config):
                return False, locale.t("config_copy_failed")
            
            dst_game_config = self.appdata_dir / 'g_The Sims 4.ini'
            if not self._create_folder_and_copy_as_admin(src_game_config, dst_game_config):
                return False, locale.t("game_config_copy_failed")
            
            dst_dll = client_path / 'version.dll'
            try:
                shutil.copy2(src_dll, dst_dll)
            except PermissionError:
                if not self._copy_file_as_admin(src_dll, dst_dll):
                    return False, locale.t("install_cancelled")
            
            if client_type == 'ea_app':
                staged_dir = client_path.parent / 'StagedEADesktop' / 'EA Desktop'
                if staged_dir.exists():
                    dst_dll_staged = staged_dir / 'version.dll'
                    try:
                        shutil.copy2(src_dll, dst_dll_staged)
                    except PermissionError:
                        self._copy_file_as_admin(src_dll, dst_dll_staged)
            
            return True, locale.t("unlocker_installed")
        except Exception as e:
            return False, locale.t("install_failed", str(e))
    
    def _delete_file_as_admin(self, file_path: Path) -> bool:
        try:
            import tempfile
            import uuid
            marker_file = Path(tempfile.gettempdir()) / f"delete_success_{uuid.uuid4().hex}.tmp"
            
            vbs_content = f'''Set objFSO = CreateObject("Scripting.FileSystemObject")
            On Error Resume Next
            objFSO.DeleteFile "{file_path}", True
            If Err.Number = 0 Then
                objFSO.CreateTextFile "{marker_file}", True
            End If
            '''
            
            vbs_file = Path(tempfile.gettempdir()) / f"admin_delete_{uuid.uuid4().hex}.vbs"
            with open(vbs_file, 'w') as f:
                f.write(vbs_content)
            
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", "wscript.exe", f'"{vbs_file}"', None, 0)
            if ret <= 32:
                try:
                    vbs_file.unlink()
                except:
                    pass
                return False
            
            import time
            max_wait = 10
            waited = 0
            while waited < max_wait:
                time.sleep(0.5)
                waited += 0.5
                if marker_file.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
                if not file_path.exists():
                    try:
                        marker_file.unlink()
                        vbs_file.unlink()
                    except:
                        pass
                    return True
            
            try:
                vbs_file.unlink()
                if marker_file.exists():
                    marker_file.unlink()
            except:
                pass
            return False
        except Exception:
            return False
    
    def uninstall_unlocker(self, locale) -> Tuple[bool, str]:
        client_type, client_path = self.get_client_info()
        if not client_path:
            return False, locale.t("ea_not_found")
        
        try:
            self._kill_client_processes(client_type)
            
            dll_path = client_path / 'version.dll'
            if dll_path.exists():
                try:
                    dll_path.unlink()
                except PermissionError:
                    if not self._delete_file_as_admin(dll_path):
                        return False, locale.t("uninstall_cancelled")
            
            if client_type == 'ea_app':
                staged_dir = client_path.parent / 'StagedEADesktop' / 'EA Desktop'
                if staged_dir.exists():
                    staged_dll = staged_dir / 'version.dll'
                    if staged_dll.exists():
                        try:
                            staged_dll.unlink()
                        except PermissionError:
                            self._delete_file_as_admin(staged_dll)
            
            if self.appdata_dir:
                anadius_dir = self.appdata_dir.parent
                if anadius_dir.exists() and anadius_dir.name == 'anadius':
                    try:
                        shutil.rmtree(anadius_dir)
                    except Exception:
                        pass
            
            if self.localappdata_dir:
                anadius_local_dir = self.localappdata_dir.parent
                if anadius_local_dir.exists() and anadius_local_dir.name == 'anadius':
                    try:
                        shutil.rmtree(anadius_local_dir)
                    except Exception:
                        pass
            
            return True, locale.t("unlocker_uninstalled")
        except Exception as e:
            return False, locale.t("uninstall_failed", str(e))


unlocker_mgr = UnlockerManager(Path(__file__).parent.parent / 'unlocker')
