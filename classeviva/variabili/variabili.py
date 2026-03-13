from datetime import datetime
import classeviva.eccezioni as e


# Constante che indica il tempo di connessione per una sessione in secondi
TEMPO_CONNESSIONE: int = 5400


# Constante che indica l'intestazione per le richieste
# Using more realistic browser headers instead of Android UA which may be blocked
# Removed Z-Dev-ApiKey when using browser UA since Classeviva validates API keys per user-agent
intestazione: dict[str, str] = {
    "content-type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Origin": "https://web.spaggiari.eu",
    "Referer": "https://web.spaggiari.eu/",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}


def valida_date(*date_: str) -> None:
    # https://stackoverflow.com/questions/16870663/how-do-i-validate-a-date-string-format-in-python
    try:
        for data in date_:
            datetime.strptime(data, r'%Y-%m-%d')
    except ValueError:
        raise e.FormatoNonValido("Formato data non valido, dev'essere YYYY-MM-DD")


def anno() -> int:
    # Return the academic-year start year:
    # if current month >= September, the academic year starts this calendar year,
    # otherwise it started the previous calendar year.
    now = datetime.now()
    return now.year if now.month >= 9 else now.year - 1


def data_inizio_anno() -> str:
    return f"{anno()}0901"


def data_fine_anno() -> str:
    return f"{anno()+1}0630"


def data_fine_anno_o_oggi() -> str:
    # Restituisce la data di fine anno scolastico o quella del giorno corrente
    end_of_school = datetime(anno()+1, 6, 30)
    if datetime.now() <= end_of_school:
        return datetime.now().strftime('%Y%m%d')
    return data_fine_anno()