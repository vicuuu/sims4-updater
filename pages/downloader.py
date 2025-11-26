import time
from pathlib import Path
from nicegui import ui
from typing import Optional, Dict, List

from libs.locale import locale_mgr
from libs.torrent import torrent_mgr, SOURCE_DIR

start_btn: Optional[ui.button] = None
stop_btn: Optional[ui.button] = None
footer_container = None
is_torrent_loaded: bool = False
download_timer = None
download_summary_label = None
current_main_container = None

CARD_MAIN = 'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl p-6 border border-purple-500/30 w-full h-full flex flex-col overflow-hidden'
CARD_FILE = 'w-full bg-gradient-to-r from-gray-800/80 to-gray-900/80 backdrop-blur rounded-xl p-3 mb-2 hover:scale-[1.01] transition-all duration-300 border border-gray-700/50 hover:border-purple-500/50'
NO_SHADOW = 'box-shadow: none'


def format_bytes(size: int) -> str:
    return f"{size / 1024*1024:.1f} MB" 


def format_eta(sec: float) -> str:
    if sec == float("inf") or sec > 86400:
        return "∞"
    m, s = divmod(int(sec), 60)
    return f"{m}m {s}s"


def update_download_summary(percent: int, count: int, peers: Optional[int] = None) -> None:
    if not download_summary_label:
        return
    
    if percent == 100:
        download_summary_label.text = f'{locale_mgr.t("downloaded")} {count} {locale_mgr.t("files")}'
        download_summary_label.classes('text-green-400', remove='text-purple-300 text-yellow-400')
    else:
        peer_info = f' | {peers} peers' if peers is not None else ''
        download_summary_label.text = f'📥 {locale_mgr.t("downloading")}: {percent}% ({count} {locale_mgr.t("files")}{peer_info})'
        
        color = 'text-yellow-400' if peers == 0 else 'text-purple-300'
        download_summary_label.classes(color, remove='text-purple-300 text-green-400 text-yellow-400')


def _create_header(name: str, file_count: int, total_size: int) -> None:
    global download_summary_label
    
    with ui.row().classes('w-full items-center gap-4 mb-4 pb-4 border-b border-purple-500/30 flex-shrink-0'):
        with ui.card().classes('bg-gradient-to-br from-purple-600 to-indigo-600 p-3 rounded-xl border-0').style(NO_SHADOW):
            ui.icon('cloud_download', size='lg').classes('text-white')
        
        with ui.column().classes('flex-grow gap-1'):
            ui.label(name).classes('text-xl font-bold text-white')
            ui.label(f'📦 {file_count} {locale_mgr.t("files")} • 💾 {format_bytes(total_size)}').classes('text-base text-purple-300')
            download_summary_label = ui.label(locale_mgr.t("ready_to_download")).classes('text-sm text-gray-400')
        
        with ui.card().classes('bg-green-500/20 backdrop-blur px-4 py-2 rounded-xl border border-green-500/50').style(NO_SHADOW):
            ui.label(locale_mgr.t("ready")).classes('text-lg font-bold text-green-400')


def _create_table_header() -> None:
    with ui.row().classes('w-full items-center gap-3 mb-3 pb-2 border-b border-gray-700/50 flex-shrink-0'):
        ui.checkbox().classes('scale-110 opacity-0 pointer-events-none')
        ui.label(locale_mgr.t("torrent_name")).classes('text-sm font-bold text-purple-300 flex-1')
        ui.label(locale_mgr.t("mod_name")).classes('text-sm font-bold text-purple-300 flex-1')
        ui.label(locale_mgr.t("download")).classes('text-sm font-bold text-purple-300 flex-1 text-center')


def _create_file_row(f, old_info: Optional[dict] = None) -> dict:
    with ui.card().classes(CARD_FILE).style(NO_SHADOW):
        with ui.row().classes('w-full items-center gap-3'):
            cb = ui.checkbox().classes('scale-110')
            if old_info:
                cb.value = old_info["checkbox"].value
            
            with ui.column().classes('flex-1 gap-0.5 min-w-0'):
                ui.label(f.name).classes('text-white font-semibold text-xs break-all')
                ui.label(format_bytes(f.length)).classes('text-gray-400 text-xs')
            
            with ui.column().classes('flex-1 gap-0.5 min-w-0'):
                ui.label(f.mod_name).classes('text-purple-300 font-bold text-sm')
            
            with ui.column().classes('flex-1 gap-1 min-w-0'):
                progress = ui.linear_progress(0)
                progress.props('color=purple-6 track-color=grey-8 size=16px rounded show-value :value-label="value => value.toFixed(1) + \'%\'"')
                
                status_label = ui.label(locale_mgr.t("waiting")).classes('text-xs text-gray-400 text-center')
                
                if old_info:
                    progress.value = old_info["progress_bar"].value
                    status_label.text = old_info["status_label"].text
                    if old_info["progress_bar"].value >= 1:
                        status_label.classes('text-green-400 font-bold', remove='text-gray-400')

    return {"file": f, "checkbox": cb, "progress_bar": progress, "status_label": status_label}


async def load_torrent(main_container) -> None:
    global is_torrent_loaded, download_summary_label, current_main_container
    
    current_main_container = main_container
    main_container.clear()

    torrents = list(SOURCE_DIR.glob("*.torrent"))
    if not torrents:
        ui.notify(locale_mgr.t("no_torrent_file"), type="warning", position="top")
        start_btn.disable()
        return

    torrent_mgr.init_session()
    success = torrent_mgr.load_all_torrents()
    
    if not success:
        ui.notify(locale_mgr.t("torrent_load_failed"), type="negative", position="top")
        start_btn.disable()
        return

    total_size = sum(f.length for f in torrent_mgr.files)
    
    with main_container:
        with ui.card().classes(CARD_MAIN).style(NO_SHADOW):
            _create_header(torrent_mgr.torrent.name, len(torrent_mgr.files), total_size)
            _create_table_header()
            
            with ui.scroll_area().classes('w-full flex-grow min-h-0'):
                torrent_mgr.files_to_download = {}
                for f in sorted(torrent_mgr.files, key=lambda x: x.name.lower()):
                    torrent_mgr.files_to_download[f.name] = _create_file_row(f)

    is_torrent_loaded = True
    start_btn.enable()
    ui.notify(f"{locale_mgr.t('loaded')} {len(torrent_mgr.handles)} {locale_mgr.t('torrents')} - {len(torrent_mgr.files)} {locale_mgr.t('files')}", type="positive", position="top")


def start_download() -> None:
    global download_timer
    
    torrent_mgr.stop_flag = False
    selected = [v for v in torrent_mgr.files_to_download.values() if v["checkbox"].value]

    if not selected:
        ui.notify(locale_mgr.t("no_files_selected"), type="warning", position="top")
        return

    start_btn.disable()
    stop_btn.enable()
    
    torrent_mgr.set_priorities(selected)
    torrent_mgr.start()
    
    if current_main_container:
        ui.timer(0.1, lambda: show_downloader_page(current_main_container), once=True)

    selected_names = [item["file"].name for item in selected]
    total_size = {item["file"].global_index: item["file"].length for item in selected}
    last_done = {item["file"].global_index: 0 for item in selected}
    last_time = [time.time()]
    last_refresh = [time.time()]

    def update_progress():
        if torrent_mgr.stop_flag:
            download_timer.active = False
            torrent_mgr.pause()
            torrent_mgr.reset_all_priorities()
            ui.notify(locale_mgr.t("download_cancelled"), type="warning", position="top")
            stop_btn.disable()
            start_btn.enable()
            return

        progress_dict = torrent_mgr.get_file_progress()
        now = time.time()
        dt = max(0.1, now - last_time[0])
        last_time[0] = now
        
        # Refresh peers every 30s
        if now - last_refresh[0] > 30:
            torrent_mgr.refresh_peers()
            last_refresh[0] = now

        all_done = True
        total_progress = 0
        
        for fname in selected_names:
            item = torrent_mgr.files_to_download.get(fname)
            if not item:
                continue
            
            global_idx = item["file"].global_index
            done = progress_dict.get(global_idx, 0)
            full = total_size[global_idx]

            ratio = done / full if full > 0 else 0
            item["progress_bar"].value = round(ratio, 3)
            total_progress += ratio

            if ratio < 1:
                all_done = False

            delta = done - last_done[global_idx]
            speed_MB = (delta / dt) / 1048576
            last_done[global_idx] = done

            eta = (full - done) / (speed_MB * 1048576) if speed_MB > 0 else float("inf")

            if ratio >= 1:
                item["status_label"].text = locale_mgr.t("completed")
                item["status_label"].classes('text-green-400 font-bold', remove='text-gray-400')
            else:
                item["status_label"].text = f"{format_bytes(done)}/{format_bytes(full)} • {speed_MB:.1f} MB/s • {format_eta(eta)}"
        
        overall_percent = int((total_progress / len(selected_names)) * 100) if selected_names else 0
        total_peers = sum(h.status().num_peers for h in torrent_mgr.handles) if torrent_mgr.handles else 0
        update_download_summary(overall_percent, len(selected_names), peers=total_peers)

        if all_done:
            download_timer.active = False
            torrent_mgr.reset_all_priorities()
            ui.notify(locale_mgr.t("all_files_downloaded"), type="positive", position="top")
            
            for fname in selected_names:
                item = torrent_mgr.files_to_download.get(fname)
                if item:
                    item["checkbox"].value = False
            
            stop_btn.disable()
            start_btn.enable()
            update_download_summary(100, len(selected_names))

    download_timer = ui.timer(0.2, update_progress)


def cancel_download() -> None:
    global download_timer
    torrent_mgr.stop_flag = True
    
    if download_timer:
        download_timer.active = False
        download_timer = None
    
    torrent_mgr.pause()
    torrent_mgr.reset_all_priorities()
    
    stop_btn.disable()
    start_btn.enable()


def show_downloader_page(main_container) -> None:
    global start_btn, stop_btn, footer_container, is_torrent_loaded, download_summary_label, current_main_container
    
    current_main_container = main_container
    main_container.clear()
    
    if is_torrent_loaded and torrent_mgr.torrent:
        total_size = sum(f.length for f in torrent_mgr.files)
        
        with main_container:
            with ui.card().classes(CARD_MAIN).style(NO_SHADOW):
                _create_header(torrent_mgr.torrent.name, len(torrent_mgr.files), total_size)
                _create_table_header()
                
                with ui.scroll_area().classes('w-full flex-grow min-h-0'):
                    new_files_dict = {}
                    
                    def sort_key(f):
                        old = torrent_mgr.files_to_download.get(f.name)
                        if old and (old["progress_bar"].value > 0 or old["checkbox"].value):
                            return (0, f.name.lower())
                        return (1, f.name.lower())
                    
                    for f in sorted(torrent_mgr.files, key=sort_key):
                        old_info = torrent_mgr.files_to_download.get(f.name)
                        new_files_dict[f.name] = _create_file_row(f, old_info)
                    
                    torrent_mgr.files_to_download = new_files_dict
    else:
        with main_container:
            with ui.card().classes('bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 rounded-2xl p-6 border border-purple-500/30 w-full h-full flex items-center justify-center').style(NO_SHADOW):
                with ui.column().classes('items-center gap-4'):
                    ui.icon('cloud_upload', size='xl').classes('text-purple-400 opacity-50')
                    ui.label(locale_mgr.t("load_torrent_to_start")).classes('text-2xl font-bold text-purple-300')
                    ui.label(locale_mgr.t("click_load_torrent")).classes('text-lg text-gray-400')
    
    _create_footer(main_container)


def _create_footer(main_container) -> None:
    global footer_container, start_btn, stop_btn
    
    if footer_container:
        footer_container.set_visibility(True)
        return
    
    with ui.footer().classes("bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white items-center justify-center gap-6 py-4 border-t border-gray-700/50") as footer:
        footer_container = footer
        
        btn_classes = 'px-6 py-2 rounded-xl text-base font-semibold transition-all duration-300'
        
        with ui.row().classes('gap-3'):
            ui.button(locale_mgr.t("load_torrent"), on_click=lambda: load_torrent(main_container), icon='file_upload') \
                .classes(f'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white {btn_classes}').props('flat')
            
            start_btn = ui.button(locale_mgr.t("start"), on_click=start_download, icon='play_arrow') \
                .classes(f'bg-green-600 hover:bg-green-700 text-white {btn_classes}').props('flat')
            if not is_torrent_loaded:
                start_btn.disable()
            
            stop_btn = ui.button(locale_mgr.t("stop"), on_click=cancel_download, icon='stop') \
                .classes(f'bg-red-600 hover:bg-red-700 text-white {btn_classes}').props('flat')
            stop_btn.disable()


def hide_downloader_footer() -> None:
    if footer_container:
        footer_container.set_visibility(False)