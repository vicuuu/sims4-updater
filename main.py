import time
import re
import os
from pathlib import Path
from nicegui import ui, app
from libs.torrent import TorrentManager, TorrentFile
from libs.locale import LocaleManager
from libs.install import installer_mgr
from libs.unlock import unlocker_mgr
from libs.utils import format_bytes, format_speed, format_eta
import tkinter as tk
from tkinter import filedialog

SOURCE_DIR = Path("source")
DOWNLOAD_DIR = Path("downloads")
LOCALES_FILE = Path(__file__).parent / "locales.json"

locale = LocaleManager(LOCALES_FILE, language="en")
torrent_mgr = TorrentManager(SOURCE_DIR, DOWNLOAD_DIR)

STATUS_NOT_INSTALLED = "not_installed"
STATUS_INSTALLED = "installed"
STATUS_DOWNLOADING = "downloading"
STATUS_INSTALLING = "installing"


class TorrentApp:
    def __init__(self):
        self.file_states = {}
        self.timer = None
        self.is_loaded = False
        self.last_bytes = {}
        self.last_time = time.time()
        self.category_sort = {}
        self.game_path = None
        self.installed_dlc = set()
        self.installed_mod_names = set()
        self.auto_install = True
        self.current_tab = 'download'
        self.header_container = None
        self.content_container = None
        self.footer_container = None
        self.btn_start = None
        self.btn_stop = None
        self.auto_install_switch = None
        self.summary_label = None
        self.status_badge = None
        self.game_path_input = None
        self.game_path_container = None
    
    def build(self):
        ui.add_head_html('<link rel="stylesheet" href="/static/styles.css">')
        ui.add_head_html('''
            <script>
                window.saveScroll=function(){const c=document.querySelector('.file-list-scroll');if(c)window._scrollPos=c.scrollTop;}
                window.restoreScroll=function(){setTimeout(function(){const c=document.querySelector('.file-list-scroll');if(c&&window._scrollPos!==undefined)c.scrollTop=window._scrollPos;},10);}
            </script>
        ''')
        with ui.element('div').classes('app-container'):
            self._build_header()
            self._build_game_path_section()
            self._build_content()
            self._build_footer()
        self._auto_detect_game()
    
    def _build_header(self):
        self.header_container = ui.element('header').classes('header')
        self._render_header()
    
    def _render_header(self):
        self.header_container.clear()
        with self.header_container:
            ui.icon('cloud_download', size='0.9rem').classes('logo-icon')
            ui.label(locale.t("app_title")).classes('logo-text')
            
            with ui.element('div').classes('tabs'):
                btn_download = ui.button(locale.t("download_tab"), on_click=lambda: self._switch_tab('download')).props('flat')
                btn_download.classes('tab-btn active' if self.current_tab == 'download' else 'tab-btn')
                btn_unlocker = ui.button(locale.t("unlocker_tab"), on_click=lambda: self._switch_tab('unlocker')).props('flat')
                btn_unlocker.classes('tab-btn active' if self.current_tab == 'unlocker' else 'tab-btn')
            
            with ui.element('div').classes('lang-switcher'):
                for lang_code in ['pl', 'en']:
                    btn = ui.button(lang_code.upper(), on_click=lambda l=lang_code: self._change_language(l)).props('flat')
                    btn.classes('btn-lang active' if locale.language == lang_code else 'btn-lang')
    
    def _build_game_path_section(self):
        self.game_path_container = ui.element('div').classes('game-path-section')
        self._render_game_path_section()
    
    def _render_game_path_section(self):
        current_path_value = self.game_path_input.value if self.game_path_input else ''
        self.game_path_container.clear()
        with self.game_path_container:
            with ui.element('div').classes('game-path-container'):
                ui.icon('folder_open', size='1.5rem').classes('game-path-icon')
                with ui.element('div').classes('game-path-input-wrapper'):
                    self.game_path_input = ui.input(placeholder='C:\\Program Files\\The Sims 4', on_change=self._on_game_path_change).classes('game-path-input').props('outlined dense')
                    self.game_path_input.value = current_path_value
                    if self.game_path:
                        self.game_path_input.classes('valid', remove='invalid')
                    elif current_path_value:
                        self.game_path_input.classes('invalid', remove='valid')
                with ui.element('div').classes('game-path-actions'):
                    ui.button(locale.t("detect"), icon='search', on_click=self._auto_detect_game).classes('btn-game-action').props('flat dense')
                    ui.button(locale.t("browse"), icon='folder_open', on_click=self._browse_folder).classes('btn-game-action').props('flat dense')
    
    def _browse_folder(self):
        try:
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', 1)
            folder = filedialog.askdirectory(title=locale.t("select_folder"), initialdir='C:/')
            root.destroy()
            if folder:
                self.game_path_input.value = folder
                self._on_game_path_change(type('obj', (object,), {'value': folder})())
        except Exception as e:
            print(f"Error: {e}")
            ui.notify(locale.t("browser_error"), type="negative", position="top-right")
    
    def _auto_detect_game(self):
        paths_to_check = [
            (drive, path) for drive in ["C", "D", "E", "F", "G", "H"]
            for path in [
                r"\Program Files (x86)\Steam\steamapps\common\The Sims 4",
                r"\Program Files\Steam\steamapps\common\The Sims 4",
                r"\SteamLibrary\steamapps\common\The Sims 4",
                r"\Program Files\EA Games\The Sims 4",
                r"\Program Files (x86)\EA Games\The Sims 4",
                r"\Program Files (x86)\Origin Games\The Sims 4",
                r"\Program Files\Origin Games\The Sims 4",
                r"\The Sims 4",
            ]
        ]
        for drive, path in paths_to_check:
            full_path = f"{drive}:{path}"
            if os.path.exists(full_path) and self._validate_game_path(full_path):
                self.game_path_input.value = full_path
                self.game_path = full_path
                installer_mgr.set_game_path(full_path)
                self._detect_installed_dlc()
                self._update_input_style(True)
                if self.auto_install_switch:
                    self.auto_install_switch.enable()
                ui.notify(locale.t("game_found", full_path), type="positive", position="top-right")
                if self.is_loaded:
                    self._render_torrent_view()
                return
        self._update_input_style(False)
        if self.auto_install_switch:
            self.auto_install_switch.disable()
        ui.notify(locale.t("game_not_found"), type="warning", position="top-right")
    
    def _on_game_path_change(self, e):
        path = e.value.strip()
        if not path:
            self._update_input_style(None)
            self.game_path = None
            installer_mgr.set_game_path("")
            self.installed_dlc.clear()
            self.installed_mod_names.clear()
            if self.auto_install_switch:
                self.auto_install_switch.disable()
            return
        if os.path.exists(path) and self._validate_game_path(path):
            self.game_path = path
            installer_mgr.set_game_path(path)
            self._detect_installed_dlc()
            self._update_input_style(True)
            if self.auto_install_switch:
                self.auto_install_switch.enable()
            if self.is_loaded:
                self._render_torrent_view()
        else:
            self.game_path = None
            installer_mgr.set_game_path("")
            self.installed_dlc.clear()
            self.installed_mod_names.clear()
            self._update_input_style(False)
            if self.auto_install_switch:
                self.auto_install_switch.disable()
    
    def _update_input_style(self, is_valid):
        if is_valid is None:
            self.game_path_input.classes(remove='valid invalid')
        elif is_valid:
            self.game_path_input.classes('valid', remove='invalid')
        else:
            self.game_path_input.classes('invalid', remove='valid')
    
    def _validate_game_path(self, path):
        if not path or not os.path.exists(path):
            return False
        path_obj = Path(path)
        return (path_obj / "Delta").exists() and (path_obj / "Game").exists()
    
    def _is_dlc_installed(self, dlc_path: Path) -> bool:
        if not dlc_path.exists() or not dlc_path.is_dir():
            return False
        return all((dlc_path / f).exists() for f in ["magalog.package", "thumbnails.package"])
    
    def _detect_installed_dlc(self):
        self.installed_dlc.clear()
        self.installed_mod_names.clear()
        if not self.game_path or not os.path.exists(self.game_path):
            return
        delta_path = Path(self.game_path) / "Delta"
        if not delta_path.exists():
            return
        try:
            dlc_pattern = re.compile(r'^(EP|GP|SP|FP)(\d{2})', re.IGNORECASE)
            for item in os.listdir(delta_path):
                match = dlc_pattern.match(item.upper())
                if match:
                    dlc_path = delta_path / item
                    if dlc_path.is_dir() and self._is_dlc_installed(dlc_path):
                        dlc_code = f"{match.group(1)}{match.group(2)}"
                        self.installed_dlc.add(dlc_code)
                        for lang in ['pl', 'en']:
                            mod_name = locale._mods.get(dlc_code, {}).get(lang, '')
                            if mod_name:
                                self.installed_mod_names.add(mod_name.lower())
        except Exception as e:
            print(f"Error: {e}")
    
    def _get_dlc_code(self, filename: str) -> str:
        filename_norm = filename.lower()
        for code in locale._mods.keys():
            if code.lower() in filename_norm:
                return code.upper()
        category = locale.get_mod_category(filename)
        if category != 'OTHER':
            mod_name = locale.get_mod_name(filename).lower()
            for code, info in locale._mods.items():
                if not code.startswith(category):
                    continue
                en_name = info.get('en', '').lower()
                pl_name = info.get('pl', '').lower()
                if mod_name in [en_name, pl_name] or en_name == mod_name or pl_name == mod_name:
                    return code.upper()
        return "—"
    
    def _is_file_installed(self, file: TorrentFile) -> bool:
        return (self.game_path and self.installed_mod_names and file.mod_name.lower().strip() in self.installed_mod_names)
    
    def _get_file_status(self, file: TorrentFile) -> str:
        if self._is_file_installed(file):
            return STATUS_INSTALLED
        state = self.file_states.get(file.name)
        if state:
            return state.get('status_type', STATUS_NOT_INSTALLED)
        return STATUS_NOT_INSTALLED
    
    def _build_content(self):
        with ui.element('main').classes('main-content'):
            with ui.element('div').classes('content-wrapper'):
                self.content_container = ui.element('div').classes('content-container')
                self._render_empty_state()
    
    def _render_empty_state(self):
        self.content_container.clear()
        with self.content_container:
            with ui.element('div').classes('empty-state'):
                ui.icon('cloud_download', size='4rem').classes('empty-icon')
                ui.label(locale.t("title")).classes('empty-title')
                ui.label(locale.t("subtitle")).classes('empty-subtitle')
    
    def _save_file_states(self) -> dict:
        return {
            name: {
                'checked': state.get('checked', False),
                'progress': state.get('progress', 0.0),
                'status_type': state.get('status_type', STATUS_NOT_INSTALLED),
            }
            for name, state in self.file_states.items()
        }
    
    def _update_mod_names(self):
        for i, file in enumerate(torrent_mgr.files):
            torrent_mgr.files[i] = TorrentFile(
                name=file.name,
                mod_name=locale.get_mod_name(file.name),
                size=file.size,
                handle_idx=file.handle_idx,
                file_idx=file.file_idx,
                global_idx=file.global_idx
            )
    
    def _group_files_by_category(self):
        categories = {'EP': [], 'GP': [], 'SP': [], 'FP': [], 'OTHER': []}
        for file in torrent_mgr.files:
            categories[locale.get_mod_category(file.name)].append(file)
        return categories
    
    def _sort_category_files(self, files: list, category: str, sort_by: str):
        reverse = sort_by.endswith('_desc')
        if sort_by.startswith('size'):
            key = lambda f: f.size
        elif sort_by.startswith('id'):
            key = lambda f: self._get_dlc_code(f.name)
        elif sort_by.startswith('installed'):
            has_installed = any(self._is_file_installed(f) for f in files)
            has_not_installed = any(not self._is_file_installed(f) for f in files)
            
            if not (has_installed and has_not_installed):
                key = lambda f: f.name.lower()
            else:
                key = lambda f: (0 if self._is_file_installed(f) else 1, f.name.lower())
        else:
            key = lambda f: f.name.lower()
        return sorted(files, key=key, reverse=reverse)
    
    def _render_torrent_view(self):
        saved_states = self._save_file_states()
        self.content_container.clear()
        meta = torrent_mgr.metadata
        
        with self.content_container:
            with ui.element('div').classes('torrent-info'):
                ui.icon('folder_special', size='1.5rem').classes('torrent-icon')
                with ui.element('div').classes('torrent-meta'):
                    ui.label(meta['name']).classes('torrent-name')
                    with ui.element('div').classes('torrent-stats'):
                        ui.label(f"📦 {meta['total_files']} {locale.t('files')}")
                        ui.label(f"💾 {format_bytes(meta['total_size'])}")
                        self.summary_label = ui.label(locale.t("ready_to_download"))
                with ui.element('div').classes('status-badge ready') as badge:
                    self.status_badge = badge
                    ui.label(locale.t("ready"))
            
            categories = self._group_files_by_category()
            with ui.element('div').classes('file-list'):
                with ui.element('div').classes('file-header'):
                    ui.element('div')
                    ui.label(locale.t("torrent_name"))
                    ui.label(locale.t("dlc_id"))
                    ui.label(locale.t("mod_name"))
                    ui.label(locale.t("status"))
                    ui.label(locale.t("download"))
                
                with ui.element('div').classes('file-list-scroll').props('onscroll="window.saveScroll()"'):
                    for category in ['EP', 'GP', 'SP', 'FP', 'OTHER']:
                        files = categories[category]
                        if not files:
                            continue
                        current_sort = self.category_sort.get(category, 'name_asc')
                        sorted_files = self._sort_category_files(files, category, current_sort)
                        category_installed = sum(1 for f in sorted_files if self._is_file_installed(f))
                        
                        with ui.element('div').classes('category-separator'):
                            with ui.element('div').classes('category-left'):
                                category_text = f"{locale.get_category_name(category)} ({len(files)})"
                                if category_installed > 0:
                                    category_text
                                ui.label(category_text).classes('category-label')
                            with ui.element('div').classes('category-actions'):
                                for btn_type, label_prefix in [('installed', locale.t('sort_installed')), ('id', 'ID'), ('name', 'A-Z'), ('size', 'SIZE')]:
                                    is_active = current_sort.startswith(btn_type)
                                    is_desc = current_sort == f'{btn_type}_desc'
                                    arrow = '↑' if is_active and not is_desc else '↓' if is_active and is_desc else ''
                                    label = f"{arrow} {label_prefix}" if is_active else label_prefix
                                    next_sort = f'{btn_type}_desc' if not is_desc else f'{btn_type}_asc'
                                    def make_handler(cat, sort_type):
                                        def handler():
                                            self.category_sort[cat] = sort_type
                                            self._render_torrent_view()
                                        return handler
                                    btn = ui.button(label, on_click=make_handler(category, next_sort)).classes('btn-sort').props('flat dense')
                                    if is_active:
                                        btn.classes('active')
                                def make_select_all(cat_files):
                                    def select():
                                        all_selected = all(
                                            self.file_states[f.name]['checkbox'].value 
                                            for f in cat_files 
                                            if f.name in self.file_states and not self._is_file_installed(f)
                                        )
                                        for f in cat_files:
                                            if f.name in self.file_states and not self._is_file_installed(f):
                                                self.file_states[f.name]['checkbox'].value = not all_selected
                                    return select
                                all_selected = all(
                                    self.file_states.get(f.name, {}).get('checkbox', type('obj', (), {'value': False})()).value
                                    for f in sorted_files 
                                    if f.name in self.file_states and not self._is_file_installed(f)
                                ) if any(f.name in self.file_states and not self._is_file_installed(f) for f in sorted_files) else False
                                select_btn_text = locale.t("deselect_all") if all_selected else locale.t("select_all")
                                ui.button(select_btn_text, on_click=make_select_all(sorted_files)).classes('btn-category-select').props('flat dense')
                        
                        for file in sorted_files:
                            self._render_file_item(file, saved_states.get(file.name))
            ui.timer(0.05, lambda: ui.run_javascript('window.restoreScroll();'), once=True)
    
    def _render_file_item(self, file: TorrentFile, old_state=None):
        is_installed = self._is_file_installed(file)
        status_type = old_state.get('status_type', STATUS_NOT_INSTALLED) if old_state else STATUS_NOT_INSTALLED
        if is_installed:
            status_type = STATUS_INSTALLED
        
        with ui.element('div').classes('file-item'):
            cb = ui.checkbox()
            if old_state:
                cb.value = old_state['checked']
            if is_installed or status_type in [STATUS_DOWNLOADING, STATUS_INSTALLING]:
                cb.value = False
                cb.disable()
            with ui.element('div').classes('file-info'):
                ui.label(file.name).classes('file-name')
                ui.label(format_bytes(file.size)).classes('file-size')
            dlc_code = self._get_dlc_code(file.name)
            ui.label(dlc_code).classes('dlc-id')
            ui.label(file.mod_name).classes('mod-name')
            status_container = ui.element('div').classes('status-column')
            with status_container:
                if status_type == STATUS_INSTALLED:
                    with ui.element('div').classes('status-installed'):
                        ui.icon('check_circle', size='1rem')
                        ui.label(locale.t("installed"))
                elif status_type == STATUS_DOWNLOADING:
                    with ui.element('div').classes('status-downloading'):
                        ui.icon('cloud_download', size='1rem')
                        ui.label(locale.t("downloading"))
                elif status_type == STATUS_INSTALLING:
                    with ui.element('div').classes('status-installing'):
                        ui.icon('install_desktop', size='1rem')
                        ui.label(locale.t("installing"))
                else:
                    with ui.element('div').classes('status-not-installed'):
                        ui.label(locale.t("not_installed"))
            with ui.element('div').classes('file-progress'):
                if is_installed:
                    ui.label('—').classes('progress-text-disabled')
                else:
                    with ui.element('div').classes('progress-bar'):
                        progress_fill = ui.element('div').classes('progress-fill')
                        progress_width = old_state['progress'] * 100 if old_state else 0
                        progress_fill.style(f"width: {progress_width}%")
                    status = ui.label(locale.t("waiting")).classes('progress-text')
        
        if not is_installed:
            self.file_states[file.name] = {
                'checkbox': cb, 'progress_fill': progress_fill, 'status': status,
                'status_container': status_container, 'checked': old_state['checked'] if old_state else False,
                'progress': old_state['progress'] if old_state else 0.0, 'status_type': status_type, 'file': file
            }
        else:
            self.file_states[file.name] = {
                'checkbox': cb, 'progress_fill': None, 'status': None, 'status_container': status_container,
                'checked': False, 'progress': 1.0, 'status_type': STATUS_INSTALLED, 'file': file
            }
    
    def _build_footer(self):
        with ui.element('footer').classes('footer'):
            self.footer_container = ui.element('div').classes('w-full flex items-center justify-center gap-3 flex-wrap')
            self._render_footer()
    
    def _render_footer(self):
        self.footer_container.clear()
        with self.footer_container:
            ui.button(locale.t("load_torrent"), on_click=self._load_torrent).classes('btn btn-primary').props('flat')
            self.btn_start = ui.button(locale.t("start"), on_click=self._start_download).classes('btn btn-success').props('flat')
            if not self.is_loaded:
                self.btn_start.disable()
            self.btn_stop = ui.button(locale.t("stop"), on_click=self._stop_download).classes('btn btn-danger').props('flat')
            self.btn_stop.disable()
            with ui.element('div').classes('auto-install-container'):
                self.auto_install_switch = ui.checkbox(value=self.auto_install, on_change=self._toggle_auto_install).classes('auto-install-checkbox')
                ui.label(locale.t("auto_install")).classes('auto-install-label')
                if not self.game_path:
                    self.auto_install_switch.disable()
    
    def _change_language(self, lang: str):
        if self.timer and self.timer.active:
            ui.notify(locale.t("cannot_change_lang"), position="top-right", type="warning")
            return
        locale.set_language(lang)
        self._render_header()
        self._render_game_path_section()  
        if self.current_tab == 'download':
            if self.is_loaded:
                self._update_mod_names()
                if self.game_path:
                    self._detect_installed_dlc()
                self._render_torrent_view()
            else:
                self._render_empty_state()
            self._render_footer()
        else:
            self._render_unlocker_view()
            self._render_unlocker_footer()
    
    def _toggle_auto_install(self, e):
        self.auto_install = e.value
    
    def _switch_tab(self, tab: str):
        self.current_tab = tab
        self._render_header()
        if tab == 'download':
            if self.is_loaded:
                self._render_torrent_view()
            else:
                self._render_empty_state()
            self._render_footer()
        else:
            self._render_unlocker_view()
            self._render_unlocker_footer()
    
    def _render_unlocker_view(self):
        self.content_container.clear()
        with self.content_container:
            with ui.element('div').classes('unlocker-container'):
                status = unlocker_mgr.get_unlocker_status()
                client_type, client_path = unlocker_mgr.get_client_info()
                with ui.element('div').classes('unlocker-section'):
                    ui.label(locale.t("unlocker_title")).classes('unlocker-title')
                    if client_type:
                        client_name = 'EA Desktop' if client_type == 'ea_app' else 'Origin'
                        with ui.element('div').classes('unlocker-status'):
                            ui.icon('check_circle' if status['installed'] else 'cancel', size='2rem').classes(
                                'status-icon-installed' if status['installed'] else 'status-icon-not-installed'
                            )
                            with ui.element('div').classes('status-info'):
                                ui.label(locale.t("installed") if status['installed'] else locale.t("not_installed")).classes('status-text')
                                ui.label(f'{client_name}: {client_path}').classes('client-path')
                                details = []
                                if status['dll']:
                                    details.append('DLL: true')
                                else:
                                    details.append('DLL: false')
                                if status['config']:
                                    details.append('Config: true')
                                else:
                                    details.append('Config: false')
                                if status['game_config']:
                                    details.append('Game config: true')
                                else:
                                    details.append('Game config: false')
                                ui.label(' | '.join(details)).classes('client-path')
                                if unlocker_mgr.appdata_dir:
                                    ui.label(f'AppData: {unlocker_mgr.appdata_dir}').classes('client-path')
                    else:
                        with ui.element('div').classes('unlocker-error'):
                            ui.icon('error', size='2rem').classes('error-icon')
                            ui.label(locale.t("ea_not_found")).classes('error-text')
                    if client_type:
                        with ui.element('div').classes('unlocker-actions'):
                            if not status['installed']:
                                ui.button(locale.t("install_unlocker_config"), icon='download', on_click=self._install_unlocker).classes('btn btn-success')
                            else:
                                ui.button(locale.t("uninstall_unlocker"), icon='delete', on_click=self._uninstall_unlocker).classes('btn btn-danger')
    
    def _render_unlocker_footer(self):
        self.footer_container.clear()
        with self.footer_container:
            ui.button(locale.t("back_to_downloads"), icon='arrow_back', on_click=lambda: self._switch_tab('download')).classes('btn btn-primary').props('flat')
    
    def _install_unlocker(self):
        success, message = unlocker_mgr.install_unlocker(locale)
        ui.notify(message, type="positive" if success else "negative", position="top-right")
        self._render_unlocker_view()
    
    def _uninstall_unlocker(self):
        success, message = unlocker_mgr.uninstall_unlocker(locale)
        ui.notify(message, type="positive" if success else "negative", position="top-right")
        self._render_unlocker_view()
    
    def _load_torrent(self):
        torrents = list(SOURCE_DIR.glob("*.torrent"))
        if not torrents:
            ui.notify(locale.t("no_torrent"), position="top-right", type="warning")
            return
        torrent_mgr.init_session()
        if not torrent_mgr.load_torrents(locale.get_mod_name):
            ui.notify(locale.t("torrent_load_failed"), position="top-right", type="negative")
            return
        self.is_loaded = True
        if self.game_path:
            self._detect_installed_dlc()
        self._render_torrent_view()
        self.btn_start.enable()
    
    def _start_download(self):
        selected = [state['file'] for state in self.file_states.values() if state['checkbox'].value and not self._is_file_installed(state['file'])]
        if not selected:
            ui.notify(locale.t("no_files_selected"), position="top-right", type="warning")
            return
        self.btn_start.disable()
        self.btn_stop.enable()
        self._update_status_badge('downloading')
        for file in selected:
            if file.name in self.file_states:
                state = self.file_states[file.name]
                state['status_type'] = STATUS_DOWNLOADING
                if state.get('status_container'):
                    state['status_container'].clear()
                    with state['status_container']:
                        with ui.element('div').classes('status-downloading'):
                            ui.icon('cloud_download', size='1rem')
                            ui.label(locale.t("downloading"))
        torrent_mgr.start_download(selected)
        self.last_bytes = {f.global_idx: 0 for f in selected}
        self.last_time = time.time()
        self.timer = ui.timer(0.25, self._update_progress)
    
    def _update_progress(self):
        if not torrent_mgr.is_active:
            self.timer.active = False
            self._update_status_badge('ready')
            self.btn_stop.disable()
            self.btn_start.enable()
            ui.notify(locale.t("download_cancelled"), position="top-right", type="warning")
            return
        
        progress = torrent_mgr.get_progress()
        stats = torrent_mgr.get_stats()
        now = time.time()
        dt = now - self.last_time
        self.last_time = now
        all_done = True
        total_progress = 0
        selected_count = 0
        completed_files = []
        
        for state in self.file_states.values():
            if not state['checkbox'].value or self._is_file_installed(state['file']):
                continue
            selected_count += 1
            file = state['file']
            done = progress.get(file.global_idx, 0)
            total = file.size
            ratio = done / total if total > 0 else 0
            state['progress'] = ratio
            if state['progress_fill']:
                state['progress_fill'].style(f"width: {ratio * 100}%")
            total_progress += ratio
            if ratio >= 1:
                if state['status_type'] == STATUS_DOWNLOADING:
                    completed_files.append(file)
                    state['status_type'] = STATUS_INSTALLING
                    if state.get('status_container'):
                        state['status_container'].clear()
                        with state['status_container']:
                            with ui.element('div').classes('status-installing'):
                                ui.icon('install_desktop', size='1rem')
                                ui.label(locale.t("installing"))
            else:
                all_done = False
            if state['status']:
                if ratio >= 1:
                    state['status'].text = locale.t("completed")
                    state['status'].style('color: var(--green-400)')
                else:
                    delta = done - self.last_bytes.get(file.global_idx, 0)
                    self.last_bytes[file.global_idx] = done
                    speed = delta / dt if dt > 0 else 0
                    eta = (total - done) / speed if speed > 0 else float("inf")
                    state['status'].text = f"{format_bytes(done)}/{format_bytes(total)} • {format_speed(speed)} • {format_eta(eta)}"
        
        overall = int((total_progress / selected_count) * 100) if selected_count else 0
        peer_text = f" | {stats['peers']} peers" if stats['peers'] > 0 else " | No peers"
        self.summary_label.text = f"📥 {locale.t('downloading')}: {overall}% ({selected_count} {locale.t('files')}{peer_text})"
        
        if completed_files and self.auto_install and self.game_path:
            ui.timer(0.1, lambda: self._install_completed_files(completed_files), once=True)
        
        if all_done:
            self.timer.active = False
            torrent_mgr.stop()
            self._update_status_badge('ready')
            for state in self.file_states.values():
                if state['checkbox'].value:
                    state['checkbox'].value = False
            self.btn_stop.disable()
            self.btn_start.enable()
            ui.notify(locale.t("all_downloaded"), position="top-right", type="positive")
    
    def _install_completed_files(self, files: list):
        if not self.game_path:
            return
        if self.summary_label:
            self.summary_label.text = locale.t("installing_dlcs", len(files))
        installed_any = False
        files_to_delete = []
        for file in files:
            file_path = None
            direct_path = DOWNLOAD_DIR / file.name
            if direct_path.exists():
                file_path = direct_path
            else:
                for found in DOWNLOAD_DIR.rglob(file.name):
                    if found.is_file():
                        file_path = found
                        break
            if file_path and file_path.exists():
                success, msg, dlc_codes = installer_mgr.install_file(file_path, delete_after=True)
                if success and dlc_codes:
                    self.installed_dlc.update(dlc_codes)
                    for dlc_code in dlc_codes:
                        for lang in ['pl', 'en']:
                            mod_name = locale._mods.get(dlc_code, {}).get(lang, '')
                            if mod_name:
                                self.installed_mod_names.add(mod_name.lower())
                    installed_any = True
                    if file.name in self.file_states:
                        state = self.file_states[file.name]
                        state['status_type'] = STATUS_INSTALLED
                        if state.get('status_container'):
                            state['status_container'].clear()
                            with state['status_container']:
                                with ui.element('div').classes('status-installed'):
                                    ui.icon('check_circle', size='1rem')
                                    ui.label(locale.t("installed"))
                    ui.notify(locale.t("dlc_installed", file.mod_name, msg), type="positive", position="top-right")
                    if file_path.exists():
                        files_to_delete.append(file_path)
                elif not success:
                    if file.name in self.file_states:
                        state = self.file_states[file.name]
                        state['status_type'] = STATUS_NOT_INSTALLED
                        if state.get('status_container'):
                            state['status_container'].clear()
                            with state['status_container']:
                                with ui.element('div').classes('status-not-installed'):
                                    ui.label(locale.t("not_installed"))
                    ui.notify(locale.t("dlc_install_failed", file.mod_name, msg), type="negative", position="top-right")
            else:
                if file.name in self.file_states:
                    state = self.file_states[file.name]
                    state['status_type'] = STATUS_NOT_INSTALLED
                    if state.get('status_container'):
                        state['status_container'].clear()
                        with state['status_container']:
                            with ui.element('div').classes('status-not-installed'):
                                ui.label(locale.t("not_installed"))
                ui.notify(locale.t("file_not_found", file.mod_name), type="negative", position="top-right")
        
        if files_to_delete:
            import gc
            import time
            gc.collect()
            time.sleep(1)
            for file_path in files_to_delete:
                try:
                    if file_path.exists():
                        file_path.unlink()
                except Exception:
                    pass
        
        if installed_any:
            self._detect_installed_dlc()
        if self.is_loaded:
            self._render_torrent_view()
        if self.summary_label:
            self.summary_label.text = locale.t("ready_to_download")
    
    def _stop_download(self):
        torrent_mgr.stop()
        if self.timer:
            self.timer.active = False
        for state in self.file_states.values():
            if state.get('status_type') == STATUS_DOWNLOADING:
                state['status_type'] = STATUS_NOT_INSTALLED
        self._update_status_badge('ready')
        self.btn_stop.disable()
        self.btn_start.enable()
    
    def _update_status_badge(self, status: str):
        if not self.status_badge:
            return
        badges = {
            'ready': ('ready', locale.t("ready")),
            'downloading': ('downloading', locale.t("downloading")),
            'paused': ('paused', locale.t("paused")),
        }
        css_class, text = badges.get(status, badges['ready'])
        self.status_badge.clear()
        self.status_badge.classes(replace=f'status-badge {css_class}')
        with self.status_badge:
            ui.label(f"{text}")


@ui.page("/")
def index():
    app_instance = TorrentApp()
    app_instance.build()


if __name__ in {"__main__", "__mp_main__"}:
    app.add_static_files('/static', str(Path(__file__).parent))
    app.on_disconnect(lambda: app.shutdown())
    ui.run(title="Downloader", port=8080, dark=True, native=True, reload=True)
