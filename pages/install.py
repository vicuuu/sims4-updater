from nicegui import ui
import asyncio

from libs.install import installer_mgr, DOWNLOAD_DIR
from libs.locale import locale_mgr

CARD_BASE = 'w-full bg-gradient-to-r from-gray-800/80 to-gray-900/80 backdrop-blur rounded-xl p-4 border border-gray-700/50'
CARD_HOVER = f'{CARD_BASE} hover:border-purple-500/50 transition-all duration-300'
NO_SHADOW = 'box-shadow: none'


async def check_game_path():
    success, path = installer_mgr.get_sims4_path()
    msg_key = "game_found" if success else "game_not_found"
    ui.notify(f'{locale_mgr.t(msg_key)}: {path}', type='positive' if success else 'negative', position='top')
    return success, path


async def install_selected_item(item_path, refresh_callback):
    ui.notify(f'{locale_mgr.t("installing")}: {item_path.name}', type='info', position='top')
    await asyncio.sleep(0.1)
    
    success, message = installer_mgr.install_item(item_path)
    ui.notify(message, type='positive' if success else 'negative', position='top')
    
    if refresh_callback:
        refresh_callback()


async def install_all_items(refresh_callback):
    items = installer_mgr.get_all_items()
    
    if not items:
        ui.notify(locale_mgr.t("no_archives"), type='warning', position='top')
        return
    
    ui.notify(f'{locale_mgr.t("installing_all")}: {len(items)} {locale_mgr.t("files")}', type='info', position='top')
    await asyncio.sleep(0.1)
    
    success, message, _ = installer_mgr.install_all_items()
    ui.notify(message, type='positive' if success else 'warning', position='top')
    
    if refresh_callback:
        refresh_callback()


def show_installer_page(main_container):
    main_container.clear()

    archives_list = None
    game_path_label = None

    def refresh_archives():
        nonlocal archives_list
        if not archives_list:
            return
        
        archives_list.clear()
        items = installer_mgr.get_all_items()
        
        with archives_list:
            if not items:
                with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                    ui.label(locale_mgr.t("no_archives_found")).classes('text-gray-400 text-center')
            else:
                for item in items:
                    _create_archive_card(item, refresh_archives)

    def _create_archive_card(item, refresh_cb):
        icon = 'folder_zip' if item.suffix.lower() == '.zip' else 'insert_drive_file'
        
        with ui.card().classes(f'{CARD_HOVER} mb-2').style(NO_SHADOW):
            with ui.row().classes('items-center gap-3 w-full'):
                ui.icon(icon, size='md').classes('text-purple-400')
                
                with ui.column().classes('flex-grow min-w-0 gap-1'):
                    ui.label(str(item.relative_to(DOWNLOAD_DIR))).classes('text-white font-semibold text-sm break-all')
                    ui.label(f'{item.stat().st_size / (1024*1024):.1f} MB').classes('text-gray-400 text-xs')
                
                ui.button(
                    locale_mgr.t("install"),
                    icon='download',
                    on_click=lambda i=item: install_selected_item(i, refresh_cb)
                ).classes('bg-green-600 hover:bg-green-700 text-white').props('dense')

    async def check_and_update_path():
        nonlocal game_path_label
        success, path = await check_game_path()
        
        if success:
            game_path_label.set_text(f'📁 {path}')
            game_path_label.classes(replace='text-green-400 font-mono text-sm')
        else:
            game_path_label.set_text(path)
            game_path_label.classes(replace='text-red-400 font-mono text-sm')

    with main_container:
        with ui.card().classes(
            'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 '
            'rounded-2xl p-6 border border-purple-500/30 w-full h-full flex flex-col'
        ).style(NO_SHADOW):

            with ui.row().classes('w-full items-center gap-4 mb-4 pb-4 border-b border-purple-500/30'):
                with ui.card().classes('bg-gradient-to-br from-purple-600 to-indigo-600 p-3 rounded-xl border-0').style(NO_SHADOW):
                    ui.icon('install_desktop', size='lg').classes('text-white')
                
                with ui.column().classes('flex-grow gap-1'):
                    ui.label(locale_mgr.t("installer_title")).classes('text-xl font-bold text-white')
                    ui.label(locale_mgr.t("auto_install_desc")).classes('text-base text-purple-300')

                with ui.column().classes('w-full gap-4'):
                    with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                        ui.label(locale_mgr.t("game_path")).classes('text-lg font-bold text-white mb-3')
                        game_path_label = ui.label(locale_mgr.t("click_check_game")).classes('text-gray-400 font-mono text-sm mb-3')
                        ui.button(
                            locale_mgr.t("check_game_path"),
                            on_click=check_and_update_path,
                            icon='search'
                        ).classes('bg-blue-600 hover:bg-blue-700 text-white').props('dense')

            with ui.scroll_area().classes('w-full flex-grow'):
                with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                    with ui.row().classes('w-full items-center justify-between mb-3'):
                        ui.label(locale_mgr.t("archives_to_install")).classes('text-lg font-bold text-white')
                        
                        with ui.row().classes('gap-2'):
                            ui.button(
                                locale_mgr.t("refresh"),
                                icon='refresh',
                                on_click=refresh_archives
                            ).classes('bg-gray-600 hover:bg-gray-700 text-white').props('dense')
                            
                            ui.button(
                                locale_mgr.t("install_all"),
                                icon='download_for_offline',
                                on_click=lambda: install_all_items(refresh_archives)
                            ).classes('bg-purple-600 hover:bg-purple-700 text-white').props('dense')

                    archives_list = ui.column().classes('w-full gap-0 m-0 p-0')

                with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                    ui.label(locale_mgr.t("installer_info_title")).classes('text-lg font-bold text-white mb-3')
                    
                    with ui.card().classes('w-full bg-blue-900/30 p-3 rounded-lg border border-blue-500/50').style(NO_SHADOW):
                        for i in range(1, 4):
                            ui.label(locale_mgr.t(f"installer_info_{i}")).classes('text-blue-200 text-xs mb-1')

    refresh_archives()