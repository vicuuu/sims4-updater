from nicegui import ui, app
from libs.locale import locale_mgr
from pages.downloader import show_downloader_page, hide_downloader_footer
from pages.unlocker import show_unlocker_page
from pages.install import show_installer_page

main_container = None
header_container = None
current_page = "downloader"

HEADER_CSS = "bg-gradient-to-r from-purple-900 via-indigo-900 to-blue-900 text-white h-20 items-center px-8 border-b border-purple-500/30"
BTN_ACTIVE = 'bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors'
BTN_INACTIVE = 'bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-colors'

BACKGROUND_CSS = '''
<style>
    body {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
        background-attachment: fixed;
        overflow: hidden;
    }
    .q-linear-progress__track { opacity: 0.3; }
</style>
'''


def build_header_content():
    """Build header content - called on init and language change"""
    header_container.clear()
    
    with header_container:
        with ui.row().classes('w-full items-center'):
            ui.label(locale_mgr.t("app_title")).classes(
                "text-3xl font-extrabold ml-3 bg-gradient-to-r from-purple-300 to-pink-300 bg-clip-text text-transparent"
            )
            ui.space()
            
            with ui.row().classes('gap-1'):
                nav_config = [
                    ("unlocker", "security"),
                    ("downloader", "download"),
                    ("installer", "install_desktop"),
                ]
                
                for name, icon in nav_config:
                    ui.button(
                        locale_mgr.t(name),
                        on_click=lambda n=name: switch_page(n),
                        icon=icon
                    ).classes(BTN_ACTIVE if name == current_page else BTN_INACTIVE).props('flat')
            
            ui.space()
            
            with ui.row().classes('gap-1 items-center'):
                for lang_code in ['pl', 'en']:
                    is_active = locale_mgr.language == lang_code
                    ui.button(lang_code.upper(), on_click=lambda l=lang_code: change_language(l)) \
                        .classes(BTN_ACTIVE if is_active else BTN_INACTIVE) \
                        .props('flat')


def switch_page(page_name: str) -> None:
    global current_page
    current_page = page_name
    
    build_header_content()
    
    if page_name == "downloader":
        show_downloader_page(main_container)
    elif page_name == "installer":
        hide_downloader_footer()
        show_installer_page(main_container)
    elif page_name == "unlocker":
        hide_downloader_footer()
        show_unlocker_page(main_container)


def change_language(lang: str) -> None:
    locale_mgr.language = lang
    locale_mgr._build_cache()
    
    build_header_content()
    
    switch_page(current_page)


@ui.page("/")
def page():
    global main_container, header_container

    ui.add_head_html(BACKGROUND_CSS)

    with ui.header(elevated=False).classes(HEADER_CSS):
        header_container = ui.row().classes('w-full')
    
    build_header_content()

    with ui.element('div').classes('flex items-center justify-center w-full h-[calc(100vh-180px)] py-6 px-8 overflow-hidden'):
        with ui.column().classes("max-w-7xl w-full h-full overflow-hidden"):
            main_container = ui.column().classes('w-full h-full overflow-hidden')
    
    switch_page("downloader")


if __name__ in {"__main__", "__mp_main__"}:
    app.on_disconnect(lambda: app.shutdown())    
    ui.run(
        title=locale_mgr.t("app_title"),
        port=8080,
        dark=True,
        native=True,
        window_size=(1400, 900),
        reload=False,
    )