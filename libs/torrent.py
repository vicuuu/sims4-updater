from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List, Any
import libtorrent as lt
import time

from libs.locale import locale_mgr

SOURCE_DIR = Path("source")
SOURCE_DIR.mkdir(exist_ok=True)

DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


@dataclass(slots=True)
class TorrentFile:
    name: str
    mod_name: str
    length: int
    handle_idx: int
    file_idx: int
    global_index: int


@dataclass(slots=True)
class TorrentInfo:
    name: str
    files: List[TorrentFile]


class TorrentManager:
    __slots__ = ('session', 'handles', 'torrent', 'files', 'files_to_download', 'stop_flag')
    
    _SETTINGS = {
        'user_agent': 'libtorrent/2.0',
        'listen_interfaces': '0.0.0.0:6881,[::]:6881',
        'enable_outgoing_utp': True,
        'enable_incoming_utp': True,
        'enable_outgoing_tcp': True,
        'enable_incoming_tcp': True,
        'announce_to_all_tiers': True,
        'announce_to_all_trackers': True,
        'aio_threads': 8,
        'connections_limit': 500,
        'active_downloads': 10,
        'active_seeds': 10,
        'max_failcount': 1,
        'min_reconnect_time': 1,
    }
    
    _DHT_ROUTERS = (
        ("router.bittorrent.com", 6881),
        ("dht.transmissionbt.com", 6881),
        ("router.utorrent.com", 6881),
    )
    
    def __init__(self):
        self.session: Optional[lt.session] = None
        self.handles: List[Any] = []
        self.torrent: Optional[TorrentInfo] = None
        self.files: List[TorrentFile] = []
        self.files_to_download: Dict[str, dict] = {}
        self.stop_flag: bool = False

    def init_session(self) -> None:
        if self.session:
            return
        
        self.session = lt.session()
        
        settings = self.session.get_settings()
        settings.update(self._SETTINGS)
        self.session.apply_settings(settings)
        
        for router, port in self._DHT_ROUTERS:
            self.session.add_dht_router(router, port)
        
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
        self.session.start_natpmp()

    def load_all_torrents(self) -> bool:
        torrent_files = list(SOURCE_DIR.glob("*.torrent"))
        if not torrent_files:
            return False
        
        self.handles.clear()
        self.files.clear()
        global_file_index = 0
        
        for torrent_file in torrent_files:
            info = lt.torrent_info(str(torrent_file))
            
            params = lt.add_torrent_params()
            params.ti = info
            params.save_path = str(DOWNLOAD_DIR)
            params.storage_mode = lt.storage_mode_t.storage_mode_sparse
            params.flags |= lt.torrent_flags.auto_managed | lt.torrent_flags.paused | lt.torrent_flags.apply_ip_filter

            handle = self.session.add_torrent(params)
            handle.prioritize_files([0] * info.num_files())
            handle.set_max_connections(200)
            handle.set_max_uploads(50)
            self.handles.append(handle)
            
            handle_idx = len(self.handles) - 1
            for file_idx in range(info.num_files()):
                file_info = info.file_at(file_idx)
                file_name = Path(file_info.path).name
                
                self.files.append(TorrentFile(
                    name=file_name,
                    mod_name=locale_mgr.get_mod_name(file_name),
                    length=file_info.size,
                    handle_idx=handle_idx,
                    file_idx=file_idx,
                    global_index=global_file_index
                ))
                global_file_index += 1
        
        if self.handles:
            first_info = self.handles[0].torrent_file()
            name = first_info.name() if len(torrent_files) == 1 else f"{len(torrent_files)} {locale_mgr.t('torrents')}"
            self.torrent = TorrentInfo(name=name, files=self.files)
            return True
        
        return False

    def set_priorities(self, selected: List[dict]) -> None:
        if not self.handles:
            return
        
        priorities = {i: [0] * h.torrent_file().num_files() for i, h in enumerate(self.handles)}
        
        for item in selected:
            f = item["file"]
            priorities[f.handle_idx][f.file_idx] = 7
        
        for handle_idx, handle in enumerate(self.handles):
            handle.prioritize_files(priorities[handle_idx])

    def start(self) -> None:
        for handle in self.handles:
            handle.force_reannounce(0, -1)
            handle.scrape_tracker()
            handle.resume()
            handle.unset_flags(lt.torrent_flags.paused)
            handle.set_flags(lt.torrent_flags.auto_managed)
        
        for i in range(20):
            time.sleep(0.1)
            if sum(h.status().num_peers for h in self.handles) > 0:
                break
    
    def refresh_peers(self) -> None:
        for handle in self.handles:
            try:
                handle.force_reannounce(0, -1)
                handle.scrape_tracker()
                handle.force_dht_announce()
            except Exception:
                pass

    def pause(self) -> None:
        for handle in self.handles:
            handle.pause()

    def remove(self) -> None:
        if self.session:
            for handle in self.handles:
                self.session.remove_torrent(handle, 0)
            self.handles.clear()

    def status(self) -> Optional[Any]:
        return self.handles[0].status() if self.handles else None
    
    def get_file_progress(self) -> Dict[int, int]:
        progress = {}
        global_idx = 0
        
        for handle in self.handles:
            for p in handle.file_progress():
                progress[global_idx] = p
                global_idx += 1
        
        return progress
    
    def reset_all_priorities(self) -> None:
        for handle in self.handles:
            handle.prioritize_files([0] * handle.torrent_file().num_files())


torrent_mgr = TorrentManager()