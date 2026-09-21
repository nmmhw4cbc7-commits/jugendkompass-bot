"""
Telegram Bot: Sendet taeglich um 07:00 Uhr die Gesamtzahl der App-Installationen
(aus Supabase, Tabelle app_analytics, event_type = 'install').

Benoetigte Bibliotheken:
    pip install python-telegram-bot==21.* supabase

Start:
    python install_count_bot.py
"""

import logging
from datetime import time
import zoneinfo

from telegram.ext import Application, ContextTypes
from supabase import create_client, Client

# -----------------------------------------------------------------------
# KONFIGURATION - HIER ANPASSEN
# -----------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = "8781032049:AAFZI03SQXmLTbYnwksFlcNPFiuPd677woc"     # TODO: eigenen Token eintragen
TELEGRAM_CHAT_ID = 8027531086                    # TODO: eigene Chat-ID eintragen

# Supabase-Projekt: Dashboard -> Project Settings -> API
SUPABASE_URL = "https://vdcdibvclaulqxfjyzpq.supabase.co"   # TODO
# WICHTIG: service_role-Key verwenden (nicht anon), damit RLS-Regeln
# das Zaehlen nicht blockieren. Dieser Key bleibt NUR auf dem Server,
# niemals im App-Client verwenden!
SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZkY2RpYnZjbGF1bHF4Zmp5enBxIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTQ1OTE4OSwiZXhwIjoyMDgxMDM1MTg5fQ.I29tT_hib4cHHfwY-Iep_lA9iSBjP0UL7xKNUb1TDyQ"  # TODO

# Zeitzone fuer den 07:00-Versand (wichtig wegen Sommer-/Winterzeit)
TIMEZONE = zoneinfo.ZoneInfo("Europe/Berlin")

# -----------------------------------------------------------------------
# LOGGING
# -----------------------------------------------------------------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------
# SUPABASE CLIENT
# -----------------------------------------------------------------------

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def get_total_installs() -> int:
    """
    Zaehlt alle Zeilen in app_analytics mit event_type = 'install'.

    Hinweis: Das zaehlt Install-EVENTS, nicht zwingend eindeutige Geraete
    (falls jemand die App neu installiert, kann ein zweites Install-Event
    entstehen). Falls du stattdessen eindeutige Geraete zaehlen willst,
    nutze die auskommentierte Variante unten (per SQL-Funktion in Supabase).
    """
    response = (
        supabase.table("app_analytics")
        .select("id", count="exact")
        .eq("event_type", "install")
        .execute()
    )
    return response.count

    # --- Alternative: eindeutige Geraete zaehlen ---
    # Dafuer in Supabase (SQL-Editor) einmalig anlegen:
    #
    # create or replace function count_unique_installs()
    # returns bigint language sql stable as $$
    #   select count(distinct device_id) from app_analytics
    #   where event_type = 'install';
    # $$;
    #
    # und dann hier statt obigem Block:
    # response = supabase.rpc("count_unique_installs").execute()
    # return response.data


# -----------------------------------------------------------------------
# TAEGLICHER JOB
# -----------------------------------------------------------------------

async def send_daily_install_count(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wird taeglich um 07:00 Uhr ausgefuehrt und sendet die Nachricht."""
    try:
        total_installs = get_total_installs()
        message = f"📊 Gesamtzahl der App-Installationen: {total_installs:,}".replace(",", ".")
    except Exception as exc:  # pragma: no cover
        logger.exception("Fehler beim Abrufen der Installationszahlen")
        message = f"⚠️ Konnte Installationszahlen nicht abrufen: {exc}"

    await context.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)


# -----------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.job_queue.run_daily(
        send_daily_install_count,
        time=time(hour=7, minute=0, tzinfo=TIMEZONE),
        name="daily_install_count",
    )

    logger.info("Bot gestartet. Warte auf 07:00 Uhr taeglich...")
    application.run_polling()


if __name__ == "__main__":
    main()
