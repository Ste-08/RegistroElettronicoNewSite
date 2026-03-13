from classeviva import Utente
from datetime import datetime
import asyncio
import re

class ClassevivaService:
    def __init__(self):
        self.utente = None
        self.is_logged_in = False
        self.error_message = None
        
        # State variables for pre-fetched data
        self.voti_cached = []
        self.note_cached = []
        self.assenze_cached = []
        self.agenda_cached = []
        self.bacheca_cached = []
        self.lezioni_cached = []
        self.didattica_cached = []
        self.periodi_cached = []

    def _log_login_debug(self, message):
        # Print with flush=True so logs are immediately visible on Render.
        print(f"[LOGIN-DEBUG] {message}", flush=True)

    def _build_login_candidates(self, username):
        raw = (username or "").strip()
        if not raw:
            return []

        # ALWAYS try the raw input first (e.g., S10376729C as typed)
        # On first attempt, only try the raw - avoid rate limiting from multiple attempts
        candidates = [raw]
        
        # Debug: log the exact candidates being generated
        self._log_login_debug(f"_build_login_candidates input={username!r} raw={raw!r} final_candidates={candidates}")
        
        return candidates

    async def login(self, username, password):
        candidates = self._build_login_candidates(username)
        self._log_login_debug(f"login start username={username!r} candidates={candidates}")
        self._log_login_debug(f"password_received pass_len={len(password)} pass_repr={password!r} pass_stripped={password.strip()!r}")
        if not candidates:
            self.is_logged_in = False
            self.error_message = "Inserisci un ID studente valido."
            self._log_login_debug("login aborted: no valid username candidates")
            return False

        last_error = None
        for idx, candidate in enumerate(candidates):
            try:
                self._log_login_debug(f"attempt #{idx+1}/{len(candidates)} uid={candidate!r}")
                self.utente = Utente(candidate, password)
                await self.utente.accedi()
                last_error = None
                self._log_login_debug(f"attempt success uid={candidate!r}")
                break
            except Exception as e:
                last_error = e
                self._log_login_debug(
                    f"attempt failed uid={candidate!r} type={type(e).__name__} msg={str(e)[:250]}"
                )
                # Add a small delay before next attempt to avoid rate limiting
                if idx < len(candidates) - 1:
                    self._log_login_debug(f"waiting 1 second before next attempt...")
                    import asyncio
                    await asyncio.sleep(1)
                continue

        if self.utente is None or last_error is not None:
            self.is_logged_in = False
            err = str(last_error) if last_error else ""
            self._log_login_debug(
                f"login failed after {len(candidates)} attempts type={type(last_error).__name__ if last_error else 'Unknown'} msg={err[:250]}"
            )
            if "422" in err or "non è corretta" in err or "PasswordNonValida" in type(last_error).__name__:
                self.error_message = "Credenziali non valide. Formati ID provati: numerico, S+ID, G+ID. Verifica password e codice studente." 
            elif "ConnectionError" in type(last_error).__name__ or "Timeout" in type(last_error).__name__:
                self.error_message = "Impossibile raggiungere il server Classeviva. Riprova tra qualche istante."
            else:
                self.error_message = f"Errore durante il login: {err}"
            return False

        try:
            # accedi() raises an exception on failure; if we reach here, login succeeded

            # Force recovery of ID and sanitize it to be strictly numeric
            raw_id = None
            if hasattr(self.utente, "id") and self.utente.id:
                raw_id = self.utente.id
            elif hasattr(self.utente, "dati") and self.utente.dati:
                raw_id = self.utente.dati.get("ident") or self.utente.dati.get("id")

            if not raw_id:
                try:
                    await self.utente.documenti()
                    raw_id = getattr(self.utente, "id", None)
                except:
                    pass

            if raw_id:
                # Keep only digits from the ID
                sanitized_id = "".join(re.findall(r"\d+", str(raw_id)))
                self.utente.id = sanitized_id
                # Keep endpoint id aligned with normalized numeric id.
                self.utente._id = sanitized_id
            
            if not getattr(self.utente, "id", None):
                self.is_logged_in = False
                self.error_message = "Impossibile recuperare l'ID studente numerico."
                return False
            
            self.is_logged_in = True
            self.error_message = None
            self._log_login_debug(f"login success normalized_id={self.utente.id!r}")

            # Pre-fetch all data immediately after login
            await self.prefetch_all()

            return True
        except Exception as e:
            self.is_logged_in = False
            err = str(e)
            self._log_login_debug(
                f"post-login flow failed type={type(e).__name__} msg={err[:250]}"
            )
            if "422" in err or "non è corretta" in err or "PasswordNonValida" in type(e).__name__:
                self.error_message = "Credenziali non valide. Controlla ID e password."
            elif "ConnectionError" in type(e).__name__ or "Timeout" in type(e).__name__:
                self.error_message = "Impossibile raggiungere il server Classeviva. Riprova tra qualche istante."
            else:
                self.error_message = f"Errore durante il login: {err}"
            return False

    async def prefetch_all(self):
        if not self.is_logged_in:
            return
            
        results = await asyncio.gather(
            self.get_voti(force_refresh=True),
            self.get_note(force_refresh=True),
            self.get_assenze(force_refresh=True),
            self.get_agenda(force_refresh=True),
            self.get_bacheca(force_refresh=True),
            self.get_lezioni(force_refresh=True),
            self.get_didattica(force_refresh=True),
            self.get_periodi(force_refresh=True),
            return_exceptions=True
        )

        # Populate cache from results
        def safe_get(idx, default=[]):
            res = results[idx]
            return default if isinstance(res, Exception) else res

        self.voti_cached = safe_get(0)
        self.note_cached = safe_get(1)
        self.assenze_cached = safe_get(2)
        self.agenda_cached = safe_get(3)
        self.bacheca_cached = safe_get(4)
        self.lezioni_cached = safe_get(5)
        self.didattica_cached = safe_get(6)
        self.periodi_cached = safe_get(7, default=[])

        # Fallbacks
        if not self.periodi_cached:
            self.periodi_cached = self._periodi_fallback_from_voti(self.voti_cached)
        if not self.lezioni_cached:
            self.lezioni_cached = self._lezioni_fallback_from_agenda(self.agenda_cached)
        if not self.bacheca_cached:
            self.bacheca_cached = self._comunicazioni_fallback(self.didattica_cached, self.note_cached, self.agenda_cached)

    async def get_agenda(self, force_refresh=False):
        if not self.is_logged_in:
            return []
        
        if not force_refresh and self.agenda_cached:
            return self.agenda_cached

        try:
            dati = await self.utente.agenda()
            eventi = dati if isinstance(dati, list) else dati.get("agenda", []) or dati.get("events") or []
            
            if not eventi:
                if not force_refresh:
                    self.agenda_cached = []
                return []

            eventi_filtrati = []
            
            for ev in eventi:
                data_str = ev.get("evtDatetimeBegin", "").split("T")[0]
                if not data_str: continue
                
                try:
                    data_evento = datetime.strptime(data_str, "%Y-%m-%d").date()
                except:
                    data_evento = self._parse_date(data_str)
                    
                nota = (ev.get("notes") or "Nessuna nota").strip()
                note_l = nota.lower()
                code = (ev.get("evtCode") or ev.get("eventCode") or "").upper()
                compito_keywords = [
                    "compit", "verific", "interrog", "test", "eserciz",
                    "homework", "quiz", "consegna", "da fare", "studio",
                ]
                eventi_filtrati.append({
                    "data": data_evento,
                    "materia": ev.get("subjectDesc", "N/A"),
                    "nota": nota,
                    "inizio": ev.get("evtDatetimeBegin"),
                    "autore": ev.get("authorName", ""),
                    "tipo": code or "EVENT",
                    "is_compito": any(k in note_l for k in compito_keywords) or code in {"COMP", "HW", "HOM", "TASK"},
                })
            
            eventi_filtrati.sort(key=lambda x: (x["data"] or date.min, x.get("inizio") or ""))
            
            if not force_refresh:
                self.agenda_cached = eventi_filtrati
            return eventi_filtrati
        except Exception as e:
            self.error_message = f"Errore nel recupero dell'agenda: {str(e)}"
            return self.agenda_cached

    def _parse_date(self, value):
        if value is None:
            return None

        raw = str(value).split("T")[0].strip()
        if not raw:
            return None

        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d"):
            try:
                return datetime.strptime(raw, fmt).date()
            except ValueError:
                continue

        return None

    def _to_float(self, value):
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(",", ".")

        # Handle values like 7+, 8-, +6, etc.
        m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)([+-])", text)
        if m:
            base = float(m.group(1))
            sign = m.group(2)
            return base + 0.25 if sign == "+" else base - 0.25

        m_prefix = re.fullmatch(r"([+-])(\d+(?:\.\d+)?)", text)
        if m_prefix:
            base = float(m_prefix.group(2))
            sign = m_prefix.group(1)
            return base + 0.25 if sign == "+" else base - 0.25

        try:
            return float(text)
        except ValueError:
            return None

    async def get_voti(self, limit=None, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.voti_cached:
            return self.voti_cached if limit is None else self.voti_cached[:limit]

        try:
            dati = await self.utente.voti()
            grades = dati if isinstance(dati, list) else (dati.get("grades") or dati.get("voti") or [])
            normalized = []

            for grade in grades or []:
                date_value = self._parse_date(
                    grade.get("evtDate")
                    or grade.get("date")
                    or grade.get("evtDatetime")
                )

                display_value = (
                    grade.get("displayValue")
                    or grade.get("evtValue")
                    or grade.get("decimalValue")
                    or "-"
                )

                numeric_value = self._to_float(
                    grade.get("decimalValue")
                    or grade.get("evtValue")
                    or grade.get("displayValue")
                )

                normalized.append(
                    {
                        "data": date_value,
                        "materia": grade.get("subjectDesc") or grade.get("subject") or "Materia",
                        "voto": str(display_value),
                        "numero": numeric_value,
                        "tipo": grade.get("componentDesc") or grade.get("evtCode") or "Valutazione",
                        "nota": (grade.get("notesForFamily") or grade.get("notes") or "").strip(),
                    }
                )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.voti_cached = normalized
            return normalized if limit is None else normalized[:limit]
        except Exception as e:
            self.error_message = f"Errore nel recupero voti: {str(e)}"
            return self.voti_cached

    async def get_assenze(self, limit=25, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.assenze_cached:
            return self.assenze_cached[:limit]

        try:
            dati = await self.utente.assenze()
            events = dati if isinstance(dati, list) else dati.get("events") or dati.get("assenze") or []
            normalized = []

            for event in events or []:
                date_value = self._parse_date(
                    event.get("evtDate")
                    or event.get("date")
                    or event.get("evtDatetimeBegin")
                )

                justified_raw = event.get("isJustified")
                justified = bool(justified_raw) if isinstance(justified_raw, bool) else str(justified_raw).lower() in {"true", "1", "yes"}

                normalized.append(
                    {
                        "data": date_value,
                        "tipo": event.get("evtCode") or event.get("eventCode") or "Assenza",
                        "giustificata": justified,
                        "descrizione": (event.get("reasonDesc") or event.get("statusDesc") or event.get("notes") or "").strip(),
                    }
                )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.assenze_cached = normalized
            return normalized[:limit]
        except Exception as e:
            self.error_message = f"Errore nel recupero assenze: {str(e)}"
            return self.assenze_cached

    async def get_note(self, limit=20, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.note_cached:
            return self.note_cached[:limit]

        try:
            dati = await self.utente.note()
            # Handle list vs dict (categories)
            raw_notes = dati if isinstance(dati, dict) else {"generali": dati} if isinstance(dati, list) else {}
            normalized = []

            for category, items in raw_notes.items():
                if not isinstance(items, list):
                    continue

                for note in items:
                    date_value = self._parse_date(
                        note.get("evtDate")
                        or note.get("date")
                        or note.get("evtDatetime")
                    )

                    normalized.append(
                        {
                            "data": date_value,
                            "categoria": category.replace("_", " ").title(),
                            "docente": note.get("authorName") or note.get("teacherName") or "Docente",
                            "testo": (note.get("evtText") or note.get("description") or note.get("notes") or "").strip(),
                        }
                    )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.note_cached = normalized
            return normalized[:limit]
        except Exception as e:
            self.error_message = f"Errore nel recupero note: {str(e)}"
            return self.note_cached

    async def get_bacheca(self, limit=15, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.bacheca_cached:
            return self.bacheca_cached[:limit]

        try:
            dati = await self.utente.bacheca()
            items = dati if isinstance(dati, list) else (dati.get("items") or dati.get("comunicazioni") or [])
            normalized = []

            for item in items or []:
                date_value = self._parse_date(
                    item.get("pubDT")
                    or item.get("pubDate")
                    or item.get("evtDate")
                )

                normalized.append(
                    {
                        "data": date_value,
                        "titolo": item.get("title") or item.get("cntTitle") or "Comunicazione",
                        "letta": bool(item.get("isRead") or item.get("read")),
                        "codice": item.get("evtCode") or item.get("code") or "",
                    }
                )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.bacheca_cached = normalized
            return normalized[:limit]
        except Exception as e:
            if not force_refresh:
                self.bacheca_cached = []
            return []

    async def get_lezioni(self, limit=20, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.lezioni_cached:
            return self.lezioni_cached[:limit]

        try:
            dati = await self.utente.lezioni()
            lessons = dati if isinstance(dati, list) else (dati.get("lessons") or dati.get("lezioni") or [])
            normalized = []

            for lesson in lessons or []:
                date_value = self._parse_date(
                    lesson.get("lessonDate")
                    or lesson.get("evtDate")
                    or lesson.get("date")
                )

                normalized.append(
                    {
                        "data": date_value,
                        "materia": lesson.get("subjectDesc") or lesson.get("subject") or "Lezione",
                        "argomento": (lesson.get("lessonArg") or lesson.get("notes") or "").strip(),
                        "durata": lesson.get("duration") or lesson.get("hours") or "",
                    }
                )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.lezioni_cached = normalized
            return normalized[:limit]
        except Exception as e:
            if not force_refresh:
                self.lezioni_cached = []
            return []

    async def get_didattica(self, limit=30, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.didattica_cached:
            return self.didattica_cached[:limit]

        try:
            dati = await self.utente.didattica()
            items = dati if isinstance(dati, list) else (dati.get("items") or dati.get("didattica") or [])
            normalized = []

            for item in items or []:
                date_value = self._parse_date(
                    item.get("publishDate")
                    or item.get("evtDate")
                    or item.get("date")
                )

                normalized.append(
                    {
                        "data": date_value,
                        "materia": item.get("subjectDesc") or item.get("subject") or "Materiale",
                        "titolo": (item.get("title") or item.get("objTitle") or "Contenuto didattico").strip(),
                        "autore": item.get("authorName") or "Docente",
                    }
                )

            normalized.sort(
                key=lambda item: item["data"] if item["data"] is not None else datetime.min.date(),
                reverse=True,
            )
            
            if not force_refresh:
                self.didattica_cached = normalized
            return normalized[:limit]
        except Exception as e:
            if not force_refresh:
                self.didattica_cached = []
            return []

    async def get_periodi(self, force_refresh=False):
        if not self.is_logged_in:
            return []

        if not force_refresh and self.periodi_cached:
            return self.periodi_cached

        try:
            dati = await self.utente.periodi()
            periods = dati if isinstance(dati, list) else (dati.get("periods") or dati.get("periodi") or [])
            normalized = []

            for p in periods or []:
                normalized.append(
                    {
                        "descrizione": p.get("desc") or p.get("description") or p.get("periodDesc") or "Periodo",
                        "inizio": self._parse_date(p.get("startDate") or p.get("dateBegin")),
                        "fine": self._parse_date(p.get("endDate") or p.get("dateEnd")),
                        "attivo": bool(p.get("isCurrent") or p.get("current")),
                    }
                )

            if not force_refresh:
                self.periodi_cached = normalized
            return normalized
        except Exception as e:
            return self.periodi_cached

    def _periodi_fallback_from_voti(self, voti):
        dated = sorted([v["data"] for v in voti if v.get("data")], reverse=False)
        if not dated:
            return []

        start = dated[0]
        end = dated[-1]
        if start >= end:
            return [{"descrizione": "Periodo unico", "inizio": start, "fine": end, "attivo": True}]

        mid_idx = len(dated) // 2
        split_date = dated[mid_idx]
        today = datetime.now().date()

        return [
            {
                "descrizione": "1° periodo",
                "inizio": start,
                "fine": split_date,
                "attivo": start <= today <= split_date,
            },
            {
                "descrizione": "2° periodo",
                "inizio": split_date,
                "fine": end,
                "attivo": split_date <= today <= end,
            },
        ]

    def _lezioni_fallback_from_agenda(self, agenda, limit=20):
        rows = []
        for e in agenda or []:
            rows.append(
                {
                    "data": e.get("data"),
                    "materia": e.get("materia") or "Lezione",
                    "argomento": (e.get("nota") or "").strip(),
                    "durata": "1H",
                }
            )

        rows.sort(key=lambda x: x.get("data") or datetime.min.date(), reverse=True)
        return rows[:limit]

    def _comunicazioni_fallback(self, didattica, note, agenda, limit=20):
        rows = []

        for d in didattica or []:
            rows.append(
                {
                    "data": d.get("data"),
                    "titolo": d.get("titolo") or f"Materiale {d.get('materia') or ''}".strip(),
                    "letta": True,
                    "codice": "DID",
                }
            )

        for n in note or []:
            text = (n.get("testo") or "").strip()
            title = text[:90] + ("..." if len(text) > 90 else "") if text else f"Nota {n.get('categoria') or ''}".strip()
            rows.append(
                {
                    "data": n.get("data"),
                    "titolo": title,
                    "letta": False,
                    "codice": "NOTA",
                }
            )

        for e in agenda or []:
            rows.append(
                {
                    "data": e.get("data"),
                    "titolo": (
                        f"Compito: {e.get('materia') or 'Materia'}"
                        if e.get("is_compito")
                        else f"Evento: {e.get('materia') or 'Agenda'}"
                    ),
                    "letta": not bool(e.get("is_compito")),
                    "codice": "TASK" if e.get("is_compito") else "EVT",
                }
            )

        rows.sort(key=lambda x: x.get("data") or datetime.min.date(), reverse=True)
        return rows[:limit]

    async def get_registro_completo(self, force_refresh=False):
        self.error_message = None
        if not self.is_logged_in:
            return {
                "agenda": [],
                "voti": [],
                "assenze": [],
                "note": [],
                "bacheca": [],
                "lezioni": [],
                "didattica": [],
                "periodi": [],
                "statistiche": {
                    "media_voti": None,
                    "assenze": 0,
                    "verifiche": 0,
                    "note": 0,
                    "lezioni": 0,
                },
            }
        
        if force_refresh:
            await self.prefetch_all()

        voti = self.voti_cached
        note = self.note_cached
        assenze = self.assenze_cached
        agenda = self.agenda_cached
        bacheca = self.bacheca_cached
        lezioni = self.lezioni_cached
        didattica = self.didattica_cached
        periodi = self.periodi_cached

        numeri = [item["numero"] for item in voti if item.get("numero") is not None]
        media = round(sum(numeri) / len(numeri), 2) if numeri else None

        return {
            "agenda": agenda,
            "voti": voti,
            "assenze": assenze,
            "note": note,
            "bacheca": bacheca,
            "lezioni": lezioni,
            "didattica": didattica,
            "periodi": periodi,
            "statistiche": {
                "media_voti": media,
                "assenze": len(assenze),
                "verifiche": len(voti),
                "note": len(note),
                "lezioni": len(lezioni),
            },
        }

# Singleton instance for the app
classeviva_service = ClassevivaService()
