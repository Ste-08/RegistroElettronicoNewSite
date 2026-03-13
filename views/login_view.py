import flet as ft
from services.classeviva_service import classeviva_service

# Compatibility fallback for different Flet versions
colors = getattr(ft, "colors", getattr(ft, "Colors", None))
icons = getattr(ft, "Icons", getattr(ft, "icons", None)) # Prefer Icons (proxy) over icons (module)

class LoginView(ft.Column):
    def __init__(self, page: ft.Page, on_login_success):
        super().__init__()
        self.main_page = page
        self.on_login_success = on_login_success
        
        self.username_field = ft.TextField(
            label="ID Studente",
            border_radius=10,
            prefix_icon=icons.PERSON,
            bgcolor=colors.with_opacity(0.1, colors.WHITE) if hasattr(colors, "with_opacity") else colors.WHITE,
            border_color=colors.BLUE_400,
        )
        
        self.password_field = ft.TextField(
            label="Password",
            password=True,
            can_reveal_password=True,
            border_radius=10,
            prefix_icon=icons.LOCK,
            bgcolor=colors.with_opacity(0.1, colors.WHITE) if hasattr(colors, "with_opacity") else colors.WHITE,
            border_color=colors.BLUE_400,
        )
        
        self.login_button = ft.ElevatedButton(
            content="Accedi",
            width=300,
            height=50,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                color=colors.WHITE,
                bgcolor=colors.BLUE_600,
            ),
            on_click=self.login_clicked
        )
        
        self.error_text = ft.Text(color=colors.RED_400, size=14)
        self.loading_ring = ft.ProgressRing(visible=False, width=30, height=30, stroke_width=2)

        self.controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(icons.SCHOOL, size=80, color=colors.BLUE_400),
                        ft.Text("Classeviva Web", size=32, weight=ft.FontWeight.BOLD),
                        ft.Text("Registro Elettronico", size=16, color=colors.GREY_400),
                        ft.Divider(height=40, color=ft.colors.TRANSPARENT if hasattr(ft, "colors") else colors.TRANSPARENT),
                        self.username_field,
                        self.password_field,
                        ft.Divider(height=20, color=ft.colors.TRANSPARENT if hasattr(ft, "colors") else colors.TRANSPARENT),
                        ft.Row([self.login_button, self.loading_ring], alignment=ft.MainAxisAlignment.CENTER),
                        self.error_text,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=10
                ),
                padding=40,
                bgcolor=colors.with_opacity(0.05, colors.WHITE) if hasattr(colors, "with_opacity") else colors.WHITE,
                border_radius=20,
                border=ft.border.all(1, colors.with_opacity(0.1, colors.WHITE) if hasattr(colors, "with_opacity") else colors.WHITE),
                width=400,
            )
        ]
        self.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        self.alignment = ft.MainAxisAlignment.CENTER

    async def login_clicked(self, e):
        if not self.username_field.value or not self.password_field.value:
            self.error_text.value = "Inserisci ID e Password"
            self.main_page.update()
            return

        self.login_button.disabled = True
        self.loading_ring.visible = True
        self.error_text.value = ""
        self.main_page.update()

        success = await classeviva_service.login(self.username_field.value, self.password_field.value)

        if success:
            await self.on_login_success()
        else:
            self.error_text.value = classeviva_service.error_message
            self.login_button.disabled = False
            self.loading_ring.visible = False
            self.page.update()
