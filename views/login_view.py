import flet as ft

# Compatibility fallback for different Flet versions
colors = getattr(ft, "colors", getattr(ft, "Colors", None))
icons = getattr(ft, "Icons", getattr(ft, "icons", None)) # Prefer Icons (proxy) over icons (module)

class LoginView(ft.Column):
    def __init__(self, page: ft.Page, on_login_success, service):
        super().__init__()
        self.main_page = page
        self.on_login_success = on_login_success
        self.service = service
        
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

        self.remember_me_checkbox = ft.Checkbox(label="Rimani collegato", value=True, check_color=colors.WHITE, fill_color=colors.BLUE_600)
        
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
                        ft.Row([
                            self.remember_me_checkbox,
                        ], alignment=ft.MainAxisAlignment.START),
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
        self.error_text.value = "Autenticazione in corso..."
        self.error_text.color = colors.BLUE_400
        self.main_page.update()

        # Phase 1: Authentication
        user_clean = self.username_field.value.strip() if self.username_field.value else ""
        success = await self.service.login(user_clean, self.password_field.value)

        if success:
            if hasattr(self.main_page, "client_storage"):
                if self.remember_me_checkbox.value:
                    self.main_page.client_storage.set("saved_user", user_clean)
                    self.main_page.client_storage.set("saved_pass", self.password_field.value)
                    self.main_page.client_storage.set("remember_me", True)
            
            self.error_text.value = "Sincronizzazione dati in corso..."
            self.main_page.update()
            # Note: prefetch_all is already called inside classeviva_service.login()
            await self.on_login_success()
        else:
            self.error_text.value = self.service.error_message
            self.error_text.color = colors.RED_400
            self.login_button.disabled = False
            self.loading_ring.visible = False
            self.main_page.update()
