import flet as ft
import asyncio
import os
from views.login_view import LoginView
from views.dashboard_view import DashboardView
from services.classeviva_service import ClassevivaService

# Compatibility fallback for different Flet versions
colors = getattr(ft, "colors", getattr(ft, "Colors", None))

async def main(page: ft.Page):
    # Per-session service: each browser session gets its own independent instance
    service = ClassevivaService()

    page.title = "Classeviva Web"
    
    # Load settings from storage safely
    saved_theme = "dark"
    seed_color = "green"
    if hasattr(page, "client_storage"):
        try:
            saved_theme = page.client_storage.get("theme_mode") or "dark"
            seed_color = page.client_storage.get("seed_color") or "green"
        except:
            pass
    
    page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
    page.theme = ft.Theme(
        font_family="Inter",
        color_scheme_seed=seed_color
    )
    
    # Prefer modern window API; keep backward compatibility for older Flet versions.
    if hasattr(page, "window") and page.window is not None:
        page.window.resizable = True
        # If we are on desktop, we can still set a decent initial size but without limits
        page.window.width = 450
        page.window.height = 800
    else:
        page.window_resizable = True
        page.window_width = 450
        page.window_height = 800
    
    # bgcolor will follow theme surface
    page.bgcolor = None 
    
    page.fonts = {
        "Inter": "https://github.com/google/fonts/raw/main/ofl/inter/Inter-VariableFont_slnt%2Cwght.ttf"
    }

    async def navigate_to_dashboard():
        page.controls.clear()
        page.add(DashboardView(page, on_logout=logout, service=service))
        page.update()

    async def logout(e):
        if hasattr(page, "client_storage"):
            page.client_storage.remove("saved_user")
            page.client_storage.remove("saved_pass")
            page.client_storage.remove("remember_me")
        page.controls.clear()
        page.add(LoginView(page, on_login_success=navigate_to_dashboard, service=service))
        page.update()

    icons = getattr(ft, "icons", None)

    # Automatic Login Check
    async def check_auto_login():
        if not hasattr(page, "client_storage"):
            page.add(LoginView(page, on_login_success=navigate_to_dashboard, service=service))
            page.update()
            return

        user = page.client_storage.get("saved_user")
        pwd = page.client_storage.get("saved_pass")
        remember = page.client_storage.get("remember_me")
        
        print(f"[DEBUG] Tentativo login automatico: user={user}, pwd={'***' if pwd else None}, remember={remember}")

        if user and pwd and remember:
            # Show a nice splash/loading during auto-login
            page.add(
                ft.Container(
                    expand=True,
                    content=ft.Column([
                        ft.Icon(icons.SCHOOL if icons else None, size=80, color=colors.BLUE_400),
                        ft.Text("Ripristino sessione...", size=20, weight=ft.FontWeight.BOLD),
                        ft.ProgressRing(width=40, height=40, stroke_width=2),
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
                )
            )
            page.update()

            success = await service.login(user, pwd)
            if success:
                await navigate_to_dashboard()
                return
        
        # Fallback to LoginView
        page.controls.clear()
        page.add(LoginView(page, on_login_success=navigate_to_dashboard, service=service))
        page.update()

    # Start flow synchronously to avoid swallowed task exceptions and blank screens.
    try:
        await check_auto_login()
    except Exception as ex:
        print(f"[ERROR] Inizializzazione pagina fallita: {ex}")
        page.controls.clear()
        page.add(LoginView(page, on_login_success=navigate_to_dashboard, service=service))
        page.update()

if __name__ == "__main__":
    import os
    # Render sets PORT at runtime (default 10000); expose it
    port_str = os.getenv("PORT", "8080")
    if not port_str: # sometimes it returns an empty string
        port_str = "8080"
    port = int(port_str)
    
    print(f"[INFO] Starting Flet app on host 0.0.0.0 and port {port}")

    # Render/headless deployment: enforce web mode when supported by current Flet API.
    app_view = None
    if hasattr(ft, "AppView") and hasattr(ft.AppView, "WEB_BROWSER"):
        app_view = ft.AppView.WEB_BROWSER
    elif hasattr(ft, "WEB_BROWSER"):
        app_view = ft.WEB_BROWSER

    # Prefer ft.run on newer Flet; keep backward compatibility with older versions.
    if hasattr(ft, "run"):
        try:
            if app_view is not None:
                ft.run(main, host="0.0.0.0", port=port, view=app_view)
            else:
                ft.run(main, host="0.0.0.0", port=port)
        except TypeError:
            if app_view is not None:
                ft.run(target=main, host="0.0.0.0", port=port, view=app_view)
            else:
                ft.run(target=main, host="0.0.0.0", port=port)
    else:
        if app_view is not None:
            ft.app(target=main, host="0.0.0.0", port=port, view=app_view)
        else:
            ft.app(target=main, host="0.0.0.0", port=port)
