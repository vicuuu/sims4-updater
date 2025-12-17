import time
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import libtorrent as lt


@dataclass(frozen=True, slots=True)
class TorrentFile:
    name: str
    mod_name: str
    size: int
    handle_idx: int
    file_idx: int
    global_idx: int


class TorrentManager:
    __slots__ = ('session', 'handles', 'files', '_active', '_source', '_download')
    
    SETTINGS = {
        'connections_limit': 800,
        'connection_speed': 500,
        'max_out_request_queue': 1500,
        'peer_connect_timeout': 7,
        'active_downloads': 20,
        'active_seeds': 20,
        'enable_dht': True,
        'enable_lsd': True,
        'enable_upnp': True,
        'announce_to_all_trackers': True,
        'prefer_udp_trackers': True,
        'aio_threads': 16,
        'cache_size': 2048,
    }
    
    DHT_ROUTERS = (
        ("router.bittorrent.com", 6881),
        ("dht.transmissionbt.com", 6881),
        ("router.utorrent.com", 6881),
    )
    
    def __init__(self, source_dir: Path, download_dir: Path):
        self._source = source_dir
        self._download = download_dir
        self.session: Optional[lt.session] = None
        self.handles: List = []
        self.files: List[TorrentFile] = []
        self._active = False
        self._source.mkdir(exist_ok=True)
        self._download.mkdir(exist_ok=True)
    
    def init_session(self) -> None:
        if self.session:
            return
        self.session = lt.session()
        settings = self.session.get_settings()
        settings.update(self.SETTINGS)
        self.session.apply_settings(settings)
        for router, port in self.DHT_ROUTERS:
            self.session.add_dht_router(router, port)
        self.session.start_dht()
        self.session.start_lsd()
        self.session.start_upnp()
    
    def load_torrents(self, get_mod_name_func) -> bool:
        torrents = list(self._source.glob("*.torrent"))
        if not torrents:
            return False
        
        self.handles.clear()
        self.files.clear()
        global_idx = 0
        
        for torrent_path in torrents:
            info = lt.torrent_info(str(torrent_path))
            params = lt.add_torrent_params()
            params.ti = info
            params.save_path = str(self._download)
            params.storage_mode = lt.storage_mode_t.storage_mode_sparse
            params.flags |= lt.torrent_flags.auto_managed | lt.torrent_flags.paused
            handle = self.session.add_torrent(params)
            handle.set_max_connections(250)
            handle.prioritize_files([0] * info.num_files())
            self.handles.append(handle)
            handle_idx = len(self.handles) - 1
            
            for file_idx in range(info.num_files()):
                file_info = info.file_at(file_idx)
                file_name = Path(file_info.path).name
                self.files.append(TorrentFile(
                    name=file_name,
                    mod_name=get_mod_name_func(file_name),
                    size=file_info.size,
                    handle_idx=handle_idx,
                    file_idx=file_idx,
                    global_idx=global_idx
                ))
                global_idx += 1
        return True
    
    def start_download(self, selected_files: List[TorrentFile]) -> None:
        self._active = True
        priorities = {i: [0] * h.torrent_file().num_files() for i, h in enumerate(self.handles)}
        for file in selected_files:
            priorities[file.handle_idx][file.file_idx] = 7
        for handle_idx, handle in enumerate(self.handles):
            handle.prioritize_files(priorities[handle_idx])
            handle.force_reannounce(0, -1)
            handle.resume()
        for _ in range(30):
            if not self._active:
                break
            time.sleep(0.1)
            if sum(h.status().num_peers for h in self.handles) > 0:
                break
    
    def get_progress(self) -> Dict[int, int]:
        progress = {}
        idx = 0
        for handle in self.handles:
            for bytes_done in handle.file_progress():
                progress[idx] = bytes_done
                idx += 1
        return progress
    
    def get_stats(self) -> Dict[str, int]:
        peers = 0
        download_rate = 0
        for handle in self.handles:
            status = handle.status()
            peers += status.num_peers
            download_rate += status.download_rate
        return {'peers': peers, 'download_rate': download_rate}
    
    def stop(self) -> None:
        self._active = False
        for handle in self.handles:
            handle.pause()
            handle.prioritize_files([0] * handle.torrent_file().num_files())
    
    @property
    def is_active(self) -> bool:
        return self._active
    
    @property
    def metadata(self) -> Dict:
        if not self.handles:
            return {}
        first_info = self.handles[0].torrent_file()
        return {
            'name': first_info.name() if len(self.handles) == 1 else f"{len(self.handles)} torrents",
            'total_files': len(self.files),
            'total_size': sum(f.size for f in self.files)
        }
