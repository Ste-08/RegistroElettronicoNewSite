import asyncio
from datetime import date, datetime, timedelta
import flet as ft

# Compatibility fallback for different Flet versions
colors = getattr(ft, "colors", getattr(ft, "Colors", None))
icons = getattr(ft, "Icons", getattr(ft, "icons", None))

# Vivid seed colors: display hex → flet seed name
SEED_COLOR_MAP = {
    "#22c55e": "green",
    "#3b82f6": "blue",
    "#ef4444": "red",
    "#a855f7": "purple",
    "#f97316": "orange",
    "#14b8a6": "teal",
    "#ec4899": "pink",
    "#f59e0b": "amber",
}
# Reverse lookup: seed name → hex
SEED_HEX_MAP = {v: k for k, v in SEED_COLOR_MAP.items()}


class DashboardView(ft.Column):
    def __init__(self, page: ft.Page, on_logout, service):
        super().__init__()
        self.main_page = page
        self.on_logout = on_logout
        self.service = service
        self.expand = True

        self.current_tab = 0
        self.current_month = date.today().replace(day=1)
        self.selected_day = date.today()

        self.voti_filter = "recenti"
        self.mail_query = ""
        self.agenda_query = ""
        self.altro_section = "menu"

        self.data = {
            "agenda": [],
            "voti": [],
            "lezioni": [],
            "assenze": [],
            "note": [],
            "bacheca": [],
            "didattica": [],
            "periodi": [],
            "statistiche": {"media_voti": None, "verifiche": 0, "assenze": 0, "note": 0, "lezioni": 0},
        }

        # User preferences with persistence
        self.pref_voto_min = 6.0
        self.seed_color = "green"  # flet seed name
        if hasattr(self.main_page, "client_storage"):
            try:
                self.pref_voto_min = float(self.main_page.client_storage.get("voto_minimo") or 6.0)
                self.seed_color = self.main_page.client_storage.get("seed_color") or "green"
            except:
                pass
        
        saved_theme = "dark"
        if hasattr(self.main_page, "client_storage"):
            try:
                saved_theme = self.main_page.client_storage.get("theme_mode") or "dark"
            except:
                pass
        self.main_page.theme_mode = ft.ThemeMode.DARK if saved_theme == "dark" else ft.ThemeMode.LIGHT
        self.main_page.theme = ft.Theme(color_scheme_seed=self.seed_color)

        self.loading = ft.ProgressBar(visible=False, color=colors.PRIMARY)
        self.error_text = ft.Text(color="#ff6767", visible=False)
        self.content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO, spacing=14)

        self.nav_items = [
            self._nav_item(icons.HOME, 0),
            self._nav_item(icons.BOOKMARK, 1),
            self._nav_item(icons.CALENDAR_MONTH, 2),
            self._nav_item(icons.MAIL, 3),
            self._nav_item(icons.MORE_HORIZ, 4),
        ]

        self.bottom_nav_container = ft.Container(
            content=ft.Row(self.nav_items, alignment=ft.MainAxisAlignment.SPACE_AROUND),
            bgcolor=self._c("#16191f", "#f0f0f0"),
            border=ft.border.only(top=ft.border.BorderSide(1, self._c("#252a33", "#d0d0d0"))),
            padding=10,
        )
        self.controls = [
            self.loading,
            ft.Container(content=self.content, expand=True, padding=0),
            self.error_text,
            self.bottom_nav_container,
        ]

    def did_mount(self):
        asyncio.create_task(self.load_data())

    def _is_dark(self):
        return self.main_page.theme_mode == ft.ThemeMode.DARK

    def _c(self, dark_val, light_val):
        """Return dark_val when in dark mode, light_val when in light mode."""
        return dark_val if self._is_dark() else light_val

    def _nav_item(self, icon, tab_idx):
        return ft.Container(
            content=ft.Icon(icon, size=30),
            padding=6,
            border_radius=10,
            ink=True,
            on_click=lambda e, idx=tab_idx: asyncio.create_task(self.switch_tab(idx)),
        )

    def _top_bar(self, title, actions=None):
        actions = actions or []
        return ft.Container(
            bgcolor=self._c("#16191f", "#f5f5f5"),
            padding=ft.padding.only(left=20, right=20, top=16, bottom=16),
            content=ft.Row(
                [
                    ft.Text(title, size=42, weight=ft.FontWeight.W_500),
                    ft.Container(expand=True),
                    *actions,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )

    def _section_title(self, text):
        return ft.Text(text, size=22, weight=ft.FontWeight.W_500)

    def _card(self, control, padding=14, color=None):
        if color is None:
            color = self._c("#1a1d24", "#ffffff")
        return ft.Container(
            content=control,
            bgcolor=color,
            padding=padding,
            border_radius=12,
            border=ft.border.all(1, self._c("#252a33", "#e0e0e0")),
        )

    def _fmt_date(self, value):
        if not value:
            return "--"
        return value.strftime("%d/%m/%Y")

    def _show_message(self, msg):
        self.main_page.snack_bar = ft.SnackBar(ft.Text(msg))
        self.main_page.snack_bar.open = True
        self.main_page.update()

    async def load_data(self, force_refresh=False):
        self.loading.visible = True
        self.error_text.visible = False
        self.main_page.update()

        payload = await self.service.get_registro_completo(force_refresh=force_refresh)
        if payload:
            self.data = payload

        self.loading.visible = False
        self.render()

    async def switch_tab(self, idx):
        self.current_tab = idx
        if idx != 4:
            self.altro_section = "menu"
        self.render()

    def render(self):
        self._sync_bottom_nav()
        self.content.controls.clear()

        if self.current_tab == 0:
            self._render_home()
        elif self.current_tab == 1:
            self._render_voti()
        elif self.current_tab == 2:
            self._render_agenda()
        elif self.current_tab == 3:
            self._render_comunicazioni()
        else:
            self._render_altro()

        self.error_text.value = self.service.error_message or ""
        self.error_text.visible = bool(self.error_text.value)
        self.main_page.update()

    def _sync_bottom_nav(self):
        # Also refresh bottom nav container colors for theme changes
        self.bottom_nav_container.bgcolor = self._c("#16191f", "#f0f0f0")
        self.bottom_nav_container.border = ft.border.only(top=ft.border.BorderSide(1, self._c("#252a33", "#d0d0d0")))
        active_hex = SEED_HEX_MAP.get(self.seed_color, "#22c55e")
        for idx, node in enumerate(self.nav_items):
            is_active = idx == self.current_tab
            node.bgcolor = self._c("#202630", "#e0e8ff") if is_active else colors.TRANSPARENT
            node.content.color = active_hex if is_active else self._c("#d0d4da", "#666666")

    def _render_home(self):
        self.content.controls.append(
            ft.Container(
                padding=20,
                bgcolor=colors.PRIMARY,
                content=ft.Column(
                    [
                        ft.Text("Buon pomeriggio, Stefano.", size=26, weight=ft.FontWeight.W_500, color="#ffffff"),
                        ft.Text(self._month_label(datetime.now()), size=14, color="#e8f9eb"),
                    ],
                    spacing=6,
                ),
            )
        )

        self.content.controls.append(self._week_chart_card())

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16), content=self._section_title("Ultimi voti")))
        for voto in self.data["voti"][:3]:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._voto_tile(voto)))
        if not self.data["voti"]:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun voto disponibile", color=self._c("#9aa3af", "#888888")))))

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16), content=self._section_title("Ultime lezioni")))
        lezioni_row = ft.Row(spacing=10, scroll=ft.ScrollMode.AUTO)
        for lesson in self.data.get("lezioni", [])[:4]:
            lezioni_row.controls.append(self._lesson_tile(lesson))
        if not lezioni_row.controls:
            lezioni_row.controls.append(self._card(ft.Text("Nessuna lezione", color=self._c("#9aa3af", "#888888"))))
        self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=lezioni_row))

        week_events = self._week_events()

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16), content=self._section_title("Compiti della settimana")))
        compiti = [e for e in week_events if e.get("is_compito")]
        if not compiti:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun compito questa settimana", color=self._c("#9aa3af", "#888888")))))
        for ev in compiti[:4]:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._agenda_event_green(ev)))

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16), content=self._section_title("Prossimi eventi")))
        if not week_events:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun evento nella settimana corrente", color=self._c("#9aa3af", "#888888")))))
        for ev in week_events[:4]:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._agenda_event_green(ev)))

    def _render_voti(self):
        self.content.controls.append(self._top_bar("Voti"))

        filters = ft.Row(
            [
                self._pill("Ultimi voti", "recenti"),
                self._pill("1° periodo", "p1"),
                self._pill("2° periodo", "p2"),
                self._pill("Generale", "generale"),
            ],
            scroll=ft.ScrollMode.AUTO,
            spacing=8,
        )
        self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=filters))

        voti_filtered = self._filtered_voti()
        if self.voti_filter == "recenti":
            # Recenti: show only latest grades list, without any average cards.
            if not voti_filtered:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun voto nel filtro selezionato", color=self._c("#9aa3af", "#888888")))))
            for voto in voti_filtered:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._voto_tile(voto)))
            return

        # p1 / p2 / generale: show overall average for selected scope + subject averages with drill-down.
        media = 0.0
        nums = [x["numero"] for x in voti_filtered if x.get("numero") is not None]
        if nums:
            media = round(sum(nums) / len(nums), 2)

        self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._voti_overview_card(media, voti_filtered)))

        subjects = self._subject_averages(voti_filtered)
        if not subjects:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessuna media disponibile", color=self._c("#9aa3af", "#888888")))))
            return

        for subject in subjects:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._subject_avg_tile(subject)))

    def _render_agenda(self):
        self.content.controls.append(
            self._top_bar(
                "Agenda",
                actions=[
                    ft.IconButton(icons.REFRESH, icon_color=colors.WHITE, on_click=lambda e: asyncio.create_task(self.load_data(force_refresh=True))),
                ],
            )
        )

        self.content.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16),
                content=ft.TextField(
                    value=self.agenda_query,
                    hint_text="Cerca evento o materia",
                    prefix_icon=icons.SEARCH,
                    filled=True,
                    on_change=self._on_agenda_search,
                ),
            )
        )

        month_row = ft.Row(
            [
                ft.IconButton(icons.CHEVRON_LEFT, on_click=self._prev_month),
                ft.Text(self._month_label(self.current_month), size=18, weight=ft.FontWeight.W_500),
                ft.IconButton(icons.CHEVRON_RIGHT, on_click=self._next_month),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
        self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=month_row))

        self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._month_calendar()))

        events = self._agenda_for_month(self.current_month)
        if self.selected_day and self.selected_day.month == self.current_month.month and self.selected_day.year == self.current_month.year:
            events = [e for e in events if e.get("data") == self.selected_day]
        if self.agenda_query.strip():
            q = self.agenda_query.strip().lower()
            events = [e for e in events if q in (e.get("materia") or "").lower() or q in (e.get("nota") or "").lower()]

        day_label = self.selected_day.strftime("%d/%m/%Y") if self.selected_day and self.selected_day.month == self.current_month.month and self.selected_day.year == self.current_month.year else "mese intero"
        self.content.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16),
                content=ft.Text(f"Giorno selezionato: {day_label}", size=13, color=self._c("#b4bbc8", "#666666")),
            )
        )

        if not events:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun evento trovato", color=self._c("#9aa3af", "#888888")))))
        for ev in events[:20]:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._agenda_event_green(ev)))

    def _render_comunicazioni(self):
        self.content.controls.append(self._top_bar("Comunicazioni"))

        self.content.controls.append(
            ft.Container(
                padding=ft.padding.symmetric(horizontal=16),
                content=ft.TextField(
                    value=self.mail_query,
                    hint_text="Cerca comunicazioni",
                    prefix_icon=icons.SEARCH,
                    filled=True,
                    on_change=self._on_mail_search,
                ),
            )
        )

        bacheca = self.data["bacheca"]
        if self.mail_query.strip():
            q = self.mail_query.strip().lower()
            bacheca = [x for x in bacheca if q in (x.get("titolo") or "").lower()]

        if not bacheca:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessuna comunicazione", color=self._c("#9aa3af", "#888888")))))
            return

        for item in bacheca:
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._mail_tile(item)))

    def _render_altro(self):
        self.content.controls.append(self._top_bar("Altro"))

        if self.altro_section != "menu":
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=ft.TextButton("< Torna al menu", on_click=self._back_to_altro_menu),
                )
            )
            self._render_altro_section()
            return

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16), content=ft.Text("Generale", size=16, color=colors.PRIMARY)))
        menu = [
            (icons.LIST_ALT, "Lezioni", "lezioni"),
            (icons.FOLDER, "Materiale didattico", "didattica"),
            (icons.INSERT_CHART, "Assenze", "assenze"),
            (icons.INFO, "Note", "note"),
            (icons.SCHEDULE, "Orario", "orario"),
            (icons.MENU_BOOK, "Scrutini", "scrutini"),
            (icons.PIE_CHART, "Statistiche", "statistiche"),
            (icons.WEB, "Web", "web"),
        ]
        for icon, label, key in menu:
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._menu_row(icon, label, on_click=lambda e, k=key: self._open_altro_section(k)),
                )
            )

        self.content.controls.append(ft.Container(padding=ft.padding.only(left=16, right=16, top=8), content=ft.Text("Altro", size=16, color=colors.PRIMARY)))
        settings = [
            (icons.SETTINGS, "Impostazioni", "settings"),
            (icons.GROUP, "Cambia account", "switch_account"),
            (icons.LOGOUT, "Esci", "logout"),
        ]
        for icon, label, action in settings:
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._menu_row(icon, label, on_click=lambda e, a=action: self._handle_altro_action(a)),
                )
            )

    def _render_altro_section(self):
        if self.altro_section == "lezioni":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Lezioni")))
            rows = self.data.get("lezioni", [])
            if not rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessuna lezione disponibile", color=self._c("#9aa3af", "#888888")))))
            for row in rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._lesson_row(row)))

        elif self.altro_section == "didattica":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Materiale didattico")))
            rows = self.data.get("didattica", [])
            if not rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun materiale disponibile", color=self._c("#9aa3af", "#888888")))))
            for row in rows:
                title = row.get("titolo") or "Materiale"
                meta = f"{row.get('materia') or 'Materia'} - {self._fmt_date(row.get('data'))}"
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Column([ft.Text(title, size=17, weight=ft.FontWeight.W_500), ft.Text(meta, size=12, color=self._c("#b4bbc8", "#666666"))], spacing=4))))

        elif self.altro_section == "assenze":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Assenze")))
            rows = self.data.get("assenze", [])
            if not rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessuna assenza", color=self._c("#9aa3af", "#888888")))))
            for row in rows:
                state = "Giustificata" if row.get("giustificata") else "Da giustificare"
                self.content.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16),
                        content=self._card(
                            ft.Row([
                                ft.Column([ft.Text(row.get("tipo") or "Assenza", size=17, weight=ft.FontWeight.W_500), ft.Text(self._fmt_date(row.get("data")), size=12, color=self._c("#b4bbc8", "#666666"))], spacing=4, expand=True),
                                ft.Text(state, size=12, color=colors.PRIMARY if row.get("giustificata") else "#ff9f43"),
                            ])
                        ),
                    )
                )

        elif self.altro_section == "note":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Note")))
            rows = self.data.get("note", [])
            if not rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessuna nota", color=self._c("#9aa3af", "#888888")))))
            for row in rows:
                self.content.controls.append(
                    ft.Container(
                        padding=ft.padding.symmetric(horizontal=16),
                        content=self._card(
                            ft.Column(
                                [
                                    ft.Row([
                                        ft.Text(row.get("categoria") or "Nota", weight=ft.FontWeight.W_600, expand=True),
                                        ft.Text(self._fmt_date(row.get("data")), size=12, color=self._c("#b4bbc8", "#666666")),
                                    ]),
                                    ft.Text((row.get("testo") or "Nessun dettaglio").strip(), size=14),
                                ],
                                spacing=6,
                            )
                        ),
                    )
                )

        elif self.altro_section == "orario":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Orario (da lezioni)")))
            grouped = {}
            for lesson in self.data.get("lezioni", []):
                d = lesson.get("data")
                if not d:
                    continue
                weekday = ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"][d.weekday()]
                grouped.setdefault(weekday, []).append(lesson.get("materia") or "Lezione")

            if not grouped:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Orario non disponibile", color=self._c("#9aa3af", "#888888")))))
            for day_name in ["Lun", "Mar", "Mer", "Gio", "Ven", "Sab", "Dom"]:
                if day_name not in grouped:
                    continue
                subjects = ", ".join(grouped[day_name][:5])
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Row([ft.Text(day_name, width=50), ft.Text(subjects, expand=True, size=14, color=self._c("#dce1e8", "#333333"))]))))

        elif self.altro_section == "scrutini":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Scrutini / Periodi")))
            rows = self.data.get("periodi", [])
            if not rows:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Text("Nessun periodo disponibile", color=self._c("#9aa3af", "#888888")))))
            for row in rows:
                range_text = f"{self._fmt_date(row.get('inizio'))} - {self._fmt_date(row.get('fine'))}"
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Row([ft.Column([ft.Text(row.get("descrizione") or "Periodo", size=17, weight=ft.FontWeight.W_500), ft.Text(range_text, size=12, color=self._c("#b4bbc8", "#666666"))], spacing=4, expand=True), ft.Text("Attivo" if row.get("attivo") else "", color=colors.PRIMARY)]))))

        elif self.altro_section == "statistiche":
            stats = self.data.get("statistiche", {})
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Statistiche")))
            cards = [
                ("Media voti", "-" if stats.get("media_voti") is None else str(stats.get("media_voti"))),
                ("Valutazioni", str(stats.get("verifiche", 0))),
                ("Assenze", str(stats.get("assenze", 0))),
                ("Note", str(stats.get("note", 0))),
                ("Lezioni", str(stats.get("lezioni", 0))),
            ]
            for label, value in cards:
                self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._card(ft.Row([ft.Text(label, expand=True), ft.Text(value, weight=ft.FontWeight.BOLD)]))))

        elif self.altro_section == "settings":
            self.content.controls.append(ft.Container(padding=ft.padding.symmetric(horizontal=16), content=self._section_title("Impostazioni")))
            
            # Voto Minimo Slider
            voto_slider = ft.Slider(
                min=4, max=10, divisions=12,
                value=self.pref_voto_min,
                label="{value}",
                on_change=self._set_voto_minimo
            )
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._card(
                        ft.Column([
                            ft.Text("Voto minimo obiettivo", weight=ft.FontWeight.BOLD),
                            ft.Text("Highlights i voti sotto questa soglia", size=12, color="#b4bbc8"),
                            voto_slider,
                        ], spacing=10)
                    )
                )
            )

            # Application Color
            current_hex = SEED_HEX_MAP.get(self.seed_color, "#22c55e")
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._card(
                        ft.Column([
                            ft.Text("Colore Applicazione", weight=ft.FontWeight.BOLD),
                            ft.Text("Scegli il colore principale", size=12, color=self._c("#b4bbc8", "#666666")),
                            ft.Row([
                                ft.Container(
                                    width=38, height=38, bgcolor=hex_col, border_radius=19,
                                    tooltip=seed_name.capitalize(),
                                    on_click=lambda _, col=seed_name: self._set_seed_color(col),
                                    border=ft.border.all(3, "#ffffff" if current_hex == hex_col else "transparent"),
                                    shadow=ft.BoxShadow(blur_radius=8, color=hex_col, spread_radius=1) if current_hex == hex_col else None,
                                    animate=ft.Animation(300, "decelerate")
                                ) for hex_col, seed_name in SEED_COLOR_MAP.items()
                            ], spacing=12, wrap=True),
                        ], spacing=10)
                    )
                )
            )

            # Theme Switcher
            theme_switch = ft.Switch(
                label="Tema Scuro",
                value=self.main_page.theme_mode == ft.ThemeMode.DARK,
                on_change=self._toggle_theme
            )
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._card(theme_switch)
                )
            )

            # GitHub Link
            self.content.controls.append(
                ft.Container(
                    padding=ft.padding.symmetric(horizontal=16),
                    content=self._card(
                        ft.ListTile(
                            leading=ft.Icon(icons.CODE),
                            title=ft.Text("GitHub Repository"),
                            subtitle=ft.Text("Vedi il codice sorgente", size=12),
                            on_click=lambda _: asyncio.create_task(self.main_page.launch_url("https://github.com/stefano/RegistroElettronicoNewSite"))
                        )
                    )
                )
            )

    def _back_to_altro_menu(self, e):
        self.altro_section = "menu"
        self.render()

    def _open_altro_section(self, section):
        if section == "web":
            asyncio.create_task(self.main_page.launch_url("https://web.spaggiari.eu"))
            self._show_message("Apertura web Classeviva")
            return
        self.altro_section = section
        self.render()

    def _handle_altro_action(self, action):
        if action == "logout" or action == "switch_account":
            if hasattr(self.main_page, "client_storage"):
                self.main_page.client_storage.remove("saved_user")
                self.main_page.client_storage.remove("saved_pass")
                self.main_page.client_storage.remove("remember_me")
            if action == "switch_account":
                self._show_message("Reindirizzamento al login...")
            return asyncio.create_task(self.on_logout(None))
        if action == "settings":
            self.altro_section = "settings"
            self.render()

    def _set_voto_minimo(self, e):
        self.pref_voto_min = float(e.control.value)
        if hasattr(self.main_page, "client_storage"):
            self.main_page.client_storage.set("voto_minimo", self.pref_voto_min)
        self.render()

    def _set_seed_color(self, color_name):
        self.seed_color = color_name
        if hasattr(self.main_page, "client_storage"):
            self.main_page.client_storage.set("seed_color", color_name)
        self.main_page.theme = ft.Theme(color_scheme_seed=color_name)
        self.main_page.update()
        self.render()

    def _toggle_theme(self, e):
        self.main_page.theme_mode = ft.ThemeMode.DARK if e.control.value else ft.ThemeMode.LIGHT
        if hasattr(self.main_page, "client_storage"):
            self.main_page.client_storage.set("theme_mode", "dark" if e.control.value else "light")
        self.main_page.update()
        self.render()

    def _week_chart_card(self):
        labels = ["LUN", "MAR", "MER", "GIO", "VEN", "SAB"]
        week_start, week_end = self._current_week_range()

        # Build counts from real agenda events in current week (Mon-Sat)
        counts = [0, 0, 0, 0, 0, 0]
        for ev in self.data.get("agenda", []):
            d = ev.get("data")
            if not d:
                continue
            if not (week_start <= d <= week_end):
                continue
            wd = d.weekday()
            if 0 <= wd <= 5:
                counts[wd] += 1

        points = ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        max_count = max(counts) if any(counts) else 1
        accent = SEED_HEX_MAP.get(self.seed_color, "#22c55e")
        for idx, count in enumerate(counts):
            bar_h = 20 + int((count / max_count) * 54)
            points.controls.append(
                ft.Column(
                    [
                        ft.Container(width=3, height=bar_h, bgcolor=self._c("#3f4b5d", "#c0c8d8"), border_radius=8),
                        ft.Container(width=12, height=12, border_radius=10, border=ft.border.all(2, accent), bgcolor=self._c("#1a1d24", "#ffffff")),
                        ft.Text(labels[idx], size=12, color=self._c("#dce1e9", "#555555")),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5,
                )
            )

        return ft.Container(
            padding=ft.padding.symmetric(horizontal=16),
            content=self._card(points, color=self._c("#171b21", "#f9f9f9"), padding=18),
        )

    def _current_week_range(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return week_start, week_end

    def _week_events(self):
        week_start, week_end = self._current_week_range()
        events = [e for e in self.data.get("agenda", []) if e.get("data") and week_start <= e["data"] <= week_end]
        events.sort(key=lambda x: (x["data"], x.get("inizio") or ""))
        return events

    def _voto_tile(self, voto):
        badge_color = "#4fd467"
        if voto.get("numero") is not None and voto["numero"] < self.pref_voto_min:
            badge_color = "#f44336"

        return self._card(
            ft.Row(
                [
                    ft.Container(width=18, height=18, border_radius=20, bgcolor=badge_color),
                    ft.Column(
                        [
                            ft.Text(voto.get("materia") or "Materia", size=18, weight=ft.FontWeight.W_500),
                            ft.Text(self._fmt_date(voto.get("data")), size=12, color=self._c("#b4bbc8", "#666666")),
                        ],
                        expand=True,
                        spacing=2,
                    ),
                    ft.Text(voto.get("voto") or "-", size=22, weight=ft.FontWeight.W_500),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

    def _lesson_tile(self, lesson):
        title = lesson.get("materia") or "Lezione"
        argomento = lesson.get("argomento") or "Nessun argomento"
        durata = str(lesson.get("durata") or "1H")

        return ft.Container(
            width=220,
            padding=16,
            border_radius=12,
            bgcolor="#4cb44f",
            content=ft.Column(
                [
                    ft.Row(
                        [
                            ft.Container(width=46, height=46, border_radius=23, bgcolor=colors.WHITE, content=ft.Icon(icons.MENU_BOOK, color="#4cb44f")),
                            ft.Container(expand=True),
                            ft.Container(
                                content=ft.Text(durata, size=14, color=colors.WHITE),
                                bgcolor=colors.with_opacity(0.22, colors.WHITE) if hasattr(colors, "with_opacity") else "#72c574",
                                padding=8,
                                border_radius=18,
                            ),
                        ]
                    ),
                    ft.Text(title, size=18, weight=ft.FontWeight.W_500, color=colors.WHITE),
                    ft.Text(argomento[:28] + ("..." if len(argomento) > 28 else ""), size=14, color="#ecffef"),
                ],
                spacing=10,
            ),
        )

    def _lesson_row(self, lesson):
        return self._card(
            ft.Row(
                [
                    ft.Text(self._fmt_date(lesson.get("data")), size=12, color=self._c("#b4bbc8", "#666666")),
                    ft.Text(lesson.get("materia") or "Lezione", weight=ft.FontWeight.W_600, expand=True),
                    ft.Text((lesson.get("argomento") or "")[:28], size=12, color=self._c("#dce1e8", "#444444")),
                ]
            )
        )

    def _agenda_event_green(self, event):
        note = (event.get("nota") or "Nessuna descrizione").strip()
        return ft.Container(
            bgcolor="#4cb44f",
            border_radius=10,
            padding=14,
            content=ft.Row(
                [
                    ft.Container(width=74, content=ft.Text("Tutto il giorno", size=12, color="#e5ffe8")),
                    ft.Column(
                        [
                            ft.Text(event.get("autore") or event.get("materia") or "Evento", size=18, weight=ft.FontWeight.W_600, color=colors.WHITE),
                            ft.Text(note, size=15, color="#eaffed"),
                        ],
                        expand=True,
                        spacing=5,
                    ),
                ],
                spacing=14,
            ),
        )

    def _pill(self, text, key):
        active = self.voti_filter == key
        return ft.Container(
            bgcolor=colors.PRIMARY if active else self._c("#42454d", "#e0e0e0"),
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=14, vertical=8),
            ink=True,
            on_click=lambda e, k=key: self._set_voti_filter(k),
            content=ft.Text(text, size=16, color="#ffffff" if active else self._c("#dddddd", "#333333")),
        )

    def _set_voti_filter(self, key):
        self.voti_filter = key
        self.render()

    def _filtered_voti(self):
        voti = self.data.get("voti", [])
        if self.voti_filter == "recenti":
            return voti[:20]

        # Prefer period data if available, fallback to split by school year midpoint
        if self.voti_filter in {"p1", "p2"}:
            if self.data.get("periodi") and len(self.data["periodi"]) >= 2:
                p_sorted = sorted(
                    [p for p in self.data["periodi"] if p.get("inizio") and p.get("fine")],
                    key=lambda p: p["inizio"],
                )
                if len(p_sorted) >= 2:
                    # Prefer explicit labels if present; fallback to first two by date.
                    p1 = next((p for p in p_sorted if "1" in (p.get("descrizione") or "") or "primo" in (p.get("descrizione") or "").lower()), p_sorted[0])
                    p2 = next((p for p in p_sorted if "2" in (p.get("descrizione") or "") or "second" in (p.get("descrizione") or "").lower()), p_sorted[1])
                    selected = p1 if self.voti_filter == "p1" else p2
                    return [
                        v
                        for v in voti
                        if (not v.get("data")) or (selected["inizio"] <= v["data"] <= selected["fine"])
                    ]

            midpoint = date(date.today().year, 1, 31)
            if self.voti_filter == "p1":
                return [v for v in voti if (not v.get("data")) or (v["data"] <= midpoint)]
            return [v for v in voti if (not v.get("data")) or (v["data"] > midpoint)]

        return voti

    def _voti_overview_card(self, media, filtered_voti):
        value = max(0.0, min(float(media) if media else 0.0, 10.0))
        ring = ft.ProgressRing(
            width=120,
            height=120,
            value=value / 10.0,
            stroke_width=10,
            color=colors.PRIMARY,
            bgcolor=self._c("#2e3340", "#e7e7e7"),
        )

        trend_values = [v["numero"] for v in filtered_voti if v.get("numero") is not None][:18]
        trend = self._trend_from_values(trend_values)

        return self._card(
            ft.Row(
                [
                    ft.Stack(
                        [
                            ring,
                            ft.Container(
                                width=120,
                                height=120,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text(f"{value:.2f}", size=20, weight=ft.FontWeight.W_500),
                            ),
                        ]
                    ),
                    ft.Container(expand=True, content=trend),
                ],
                spacing=16,
            ),
            padding=16,
        )

    def _trend_from_values(self, values):
        if not values:
            return ft.Text("Nessun andamento disponibile", color="#9aa3af")

        bars = ft.Row(spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        max_val = max(values)
        min_val = min(values)
        span = max(0.1, max_val - min_val)

        for val in values:
            h = 18 + int(((val - min_val) / span) * 70)
            bars.controls.append(ft.Container(width=7, height=h, bgcolor=colors.PRIMARY, border_radius=6))

        return ft.Column(
            [
                ft.Text("Media", size=16, color=self._c("#f2f4f7", "#333333")),
                ft.Container(height=92, alignment=ft.Alignment(-1, 1), content=bars),
            ],
            spacing=8,
            alignment=ft.MainAxisAlignment.END,
        )

    def _subject_averages(self, voti):
        grouped = {}
        for voto in voti:
            materia = voto.get("materia") or "Materia"
            if voto.get("numero") is None:
                continue
            grouped.setdefault(materia, []).append(
                {
                    "numero": voto["numero"],
                    "voto": voto.get("voto") or "-",
                    "data": voto.get("data"),
                }
            )

        out = []
        for materia, entries in grouped.items():
            vals = [x["numero"] for x in entries]
            avg = sum(vals) / len(vals)
            hint = "Puoi stare tranquillo!" if avg >= 7 else "Serve attenzione"

            # Show newest grades first in subject details.
            entries.sort(key=lambda x: x["data"] if x.get("data") else datetime.min.date(), reverse=True)
            out.append(
                {
                    "materia": materia.upper(),
                    "media": round(avg, 2),
                    "hint": hint,
                    "voti": [x["voto"] for x in entries],
                    "dettagli": [
                        {
                            "voto": x["voto"],
                            "data": x["data"],
                        }
                        for x in entries
                    ],
                }
            )

        out.sort(key=lambda x: x["media"], reverse=True)
        return out[:20]

    def _subject_avg_tile(self, row):
        val = max(0.0, min(row["media"], 10.0))
        color = colors.PRIMARY if val >= self.pref_voto_min else "#f44336"
        ring = ft.ProgressRing(
            width=72,
            height=72,
            value=val / 10.0,
            stroke_width=7,
            color=color,
            bgcolor=self._c("#2e3340", "#ececec"),
        )

        voti_text = ", ".join(row.get("voti", []))
        if not voti_text:
            voti_text = "Nessun voto disponibile"

        return self._card(
            ft.Row(
                [
                    ft.Stack(
                        [
                            ring,
                            ft.Container(
                                width=72,
                                height=72,
                                alignment=ft.Alignment(0, 0),
                                content=ft.Text(f"{val:.2f}", size=14, weight=ft.FontWeight.W_500),
                            ),
                        ]
                    ),
                    ft.Column(
                        [
                            ft.Text(row["materia"], size=20, weight=ft.FontWeight.W_500),
                            ft.Text(f"Media: {row['media']:.2f}", size=13, color=self._c("#d8dee7", "#444444")),
                            ft.Text(row["hint"], size=15, color=self._c("#e2e6ea", "#333333")),
                            ft.Text(f"Voti: {voti_text}", size=12, color=self._c("#b9c1cc", "#666666")),
                        ],
                        spacing=3,
                    ),
                ],
                spacing=16,
                alignment=ft.MainAxisAlignment.START,
            )
        )

    def _open_subject_details(self, row):
        detail_rows = row.get("dettagli") or []

        items = []
        if not detail_rows:
            items.append(ft.Text("Nessun voto disponibile", color="#9aa3af"))
        else:
            for item in detail_rows:
                items.append(
                    self._card(
                        ft.Row(
                            [
                                ft.Text(item.get("voto") or "-", size=18, weight=ft.FontWeight.W_600),
                                ft.Container(expand=True),
                                ft.Text(self._fmt_date(item.get("data")), size=12, color="#b4bbc8"),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=10,
                        color="#141820",
                    )
                )

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"{row['materia']} - Media {row['media']:.2f}"),
            content=ft.Container(
                width=420,
                height=420,
                content=ft.Column(items, scroll=ft.ScrollMode.AUTO, spacing=8),
            ),
            actions=[ft.TextButton("Chiudi", on_click=lambda e: self._close_dialog())],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        if hasattr(self.main_page, "open") and hasattr(self.main_page, "update"):
            self.main_page.open(dialog)
            self.main_page.update()
        else:
            self.main_page.dialog = dialog
            dialog.open = True
            self.main_page.update()

    def _close_dialog(self):
        if hasattr(self.main_page, "close") and self.main_page.dialog:
            self.main_page.close(self.main_page.dialog)
            return

        if self.main_page.dialog:
            self.main_page.dialog.open = False
            self.main_page.update()

    def _menu_row(self, icon, label, on_click):
        return ft.Container(
            content=self._card(
                ft.Row(
                    [
                        ft.Icon(icon, color=colors.PRIMARY, size=24),
                        ft.Text(label, expand=True, size=16),
                        ft.Icon(icons.CHEVRON_RIGHT, color="#9aa3af", size=20),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            ),
            ink=True,
            on_click=on_click,
            border_radius=12,
        )

    def _mail_tile(self, item):
        unread = not item.get("letta")
        mail_color = "#ff4b46" if unread else colors.PRIMARY

        return self._card(
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(item.get("titolo") or "Comunicazione", size=17, weight=ft.FontWeight.W_500),
                            ft.Text(self._fmt_date(item.get("data")), size=12, color=self._c("#b4bbc8", "#666666")),
                        ],
                        spacing=3,
                        expand=True,
                    ),
                    ft.Icon(icons.MAIL, color=mail_color, size=34),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            )
        )

    def _month_label(self, dt):
        months = [
            "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
            "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
        ]
        return f"{months[dt.month - 1]} {dt.year}"

    def _agenda_for_month(self, month_date):
        events = []
        for ev in self.data["agenda"]:
            ev_date = ev.get("data")
            if ev_date and ev_date.month == month_date.month and ev_date.year == month_date.year:
                events.append(ev)
        events.sort(key=lambda x: x["data"])
        return events

    def _month_calendar(self):
        first = self.current_month
        first_weekday = first.weekday()

        if first.month == 12:
            next_month = date(first.year + 1, 1, 1)
        else:
            next_month = date(first.year, first.month + 1, 1)
        days_count = (next_month - first).days

        event_days = {}
        for ev in self._agenda_for_month(self.current_month):
            day = ev["data"].day
            event_days[day] = event_days.get(day, 0) + 1

        week_header = ft.Row(
            [ft.Text(x, size=12, color=self._c("#808793", "#888888")) for x in ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        grid = ft.Column(spacing=8)
        day = 1
        for row_idx in range(6):
            row_cells = []
            for col_idx in range(7):
                idx = row_idx * 7 + col_idx
                if idx < first_weekday or day > days_count:
                    row_cells.append(ft.Container(width=40, height=40))
                    continue

                is_today = (day == date.today().day and first.month == date.today().month and first.year == date.today().year)
                is_selected = (
                    self.selected_day is not None
                    and day == self.selected_day.day
                    and first.month == self.selected_day.month
                    and first.year == self.selected_day.year
                )
                dot_count = min(event_days.get(day, 0), 4)
                dots = ft.Row(
                    [ft.Container(width=6, height=6, border_radius=3, bgcolor="#45bb50") for _ in range(dot_count)],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=2,
                )

                row_cells.append(
                    ft.Column(
                        [
                            ft.Container(
                                width=40,
                                height=40,
                                border_radius=20,
                                alignment=ft.Alignment(0, 0),
                                bgcolor="#45bb50" if (is_selected or is_today) else colors.TRANSPARENT,
                                ink=True,
                                on_click=lambda e, d=day: self._select_day(d),
                                content=ft.Text(str(day), color="#ffffff" if (is_selected or is_today) else self._c("#f2f3f5", "#222222"), size=16),
                            ),
                            dots,
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=2,
                    )
                )
                day += 1

            grid.controls.append(ft.Row(row_cells, alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        return self._card(ft.Column([week_header, grid], spacing=10), padding=14)

    def _prev_month(self, e):
        year = self.current_month.year
        month = self.current_month.month - 1
        if month < 1:
            year -= 1
            month = 12
        self.current_month = date(year, month, 1)
        self.selected_day = None
        self.render()

    def _next_month(self, e):
        year = self.current_month.year
        month = self.current_month.month + 1
        if month > 12:
            year += 1
            month = 1
        self.current_month = date(year, month, 1)
        self.selected_day = None
        self.render()

    def _select_day(self, day):
        self.selected_day = date(self.current_month.year, self.current_month.month, day)
        self.render()

    def _on_mail_search(self, e):
        self.mail_query = e.control.value or ""
        self.render()

    def _on_agenda_search(self, e):
        self.agenda_query = e.control.value or ""
        self.render()
