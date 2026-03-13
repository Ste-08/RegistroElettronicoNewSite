import flet as ft
import asyncio
from views.login_view import LoginView
from views.dashboard_view import DashboardView

# Compatibility fallback for different Flet versions
colors = getattr(ft, "colors", getattr(ft, "Colors", None))

async def main(page: ft.Page):
    page.title = "Classeviva Web"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width = 450
    page.window_height = 800
    page.window_resizable = True
    page.bgcolor = colors.GREY_900
    page.fonts = {
        "Inter": "https://github.com/google/fonts/raw/main/ofl/inter/Inter-VariableFont_slnt%2Cwght.ttf"
    }
    page.theme = ft.Theme(font_family="Inter")
    
    page.padding = 0

    async def navigate_to_dashboard():
        page.controls.clear()
        page.add(DashboardView(page, on_logout=logout))
        page.update()

    async def logout(e):
        page.controls.clear()
        page.add(LoginView(page, on_login_success=navigate_to_dashboard))
        page.update()

    # Initial view
    page.add(LoginView(page, on_login_success=navigate_to_dashboard))
    page.update()

if __name__ == "__main__":
    ft.run(main, view=ft.AppView.WEB_BROWSER)
