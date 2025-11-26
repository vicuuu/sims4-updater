from nicegui import ui
import asyncio

from libs.unlocker import unlocker_mgr
from libs.locale import locale_mgr


CARD_BASE = 'w-full bg-gradient-to-r from-gray-800/80 to-gray-900/80 backdrop-blur rounded-xl p-4 border border-gray-700/50'
NO_SHADOW = 'box-shadow: none'


async def check_status_with_delay(status_labels: dict) -> None:
    for key in ('unlocker', 'sims4'):
        status_labels[key].set_text(f'{locale_mgr.t("checking")}')
        status_labels[key].classes(replace='text-yellow-400 font-bold')
    
    await asyncio.sleep(0.3)
    
    checks = {
        'unlocker': (unlocker_mgr.is_unlocker_installed(), 'text-green-400', 'text-red-400'),
        'sims4': (unlocker_mgr.is_sims4_installed(), 'text-green-400', 'text-gray-400'),
    }
    
    for key, (is_installed, ok_class, fail_class) in checks.items():
        text_key = "installed" if is_installed else "not_installed"
        status_labels[key].set_text(locale_mgr.t(text_key))
        status_labels[key].classes(replace=f'{ok_class if is_installed else fail_class} font-bold')


async def install_unlocker_with_sims(status_labels: dict) -> None:
    success, message = unlocker_mgr.install_with_sims4()
    ui.notify(message, type='positive' if success else 'negative')
    if success:
        await check_status_with_delay(status_labels)


async def uninstall_unlocker(status_labels: dict) -> None:
    success, message = unlocker_mgr.uninstall_unlocker()
    ui.notify(message, type='positive' if success else 'negative')
    if success:
        await check_status_with_delay(status_labels)


def show_unlocker_page(main_container) -> None:
    main_container.clear()
    status_labels = {}
    
    with main_container:
        with ui.card().classes(
            'bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 '
            'rounded-2xl p-6 border border-purple-500/30 w-full h-full flex flex-col'
        ).style(NO_SHADOW):
            
            with ui.row().classes('w-full items-center gap-4 mb-4 pb-4 border-b border-purple-500/30 flex-shrink-0'):
                with ui.card().classes('bg-gradient-to-br from-purple-600 to-indigo-600 p-3 rounded-xl border-0').style(NO_SHADOW):
                    ui.icon('security', size='lg').classes('text-white')
                
                with ui.column().classes('flex-grow gap-1'):
                    ui.label(locale_mgr.t("unlocker_title")).classes('text-xl font-bold text-white')
                    ui.label(locale_mgr.t("one_click_install")).classes('text-base text-purple-300')

                with ui.column().classes('w-full gap-4'):
                    with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                        ui.label(locale_mgr.t("installation_status")).classes('text-lg font-bold text-white mb-3')
                        
                        for key, label_text in [('unlocker', 'version.dll'), ('sims4', 'config.ini')]:
                            with ui.row().classes('gap-2 items-center mb-2'):
                                ui.label(label_text).classes('text-sm text-gray-300 w-40')
                                status_labels[key] = ui.label(locale_mgr.t("click_check_status")).classes('text-gray-500 font-bold')

                        ui.button(
                            locale_mgr.t("check_status"),
                            on_click=lambda: check_status_with_delay(status_labels),
                            icon='refresh'
                        ).classes('bg-blue-600 hover:bg-blue-700 text-white mt-1').props('dense')
                    
                    with ui.card().classes(CARD_BASE).style(NO_SHADOW):
                        ui.label(locale_mgr.t("unlocker_management")).classes('text-lg font-bold text-white mb-3')
                        
                        with ui.card().classes('w-full bg-blue-900/30 p-3 rounded-lg border border-blue-500/50 mb-3').style(NO_SHADOW):
                            ui.label(locale_mgr.t("admin_rights_required")).classes('text-blue-200 text-xs')
                        
                        with ui.row().classes('gap-2 flex-wrap'):
                            ui.button(
                                locale_mgr.t("install_unlocker"),
                                on_click=lambda: install_unlocker_with_sims(status_labels),
                                icon='download'
                            ).classes('bg-green-600 hover:bg-green-700 text-white').props('dense')
                            
                            ui.button(
                                locale_mgr.t("uninstall_unlocker"),
                                on_click=lambda: uninstall_unlocker(status_labels),
                                icon='delete'
                            ).classes('bg-red-600 hover:bg-red-700 text-white').props('dense')