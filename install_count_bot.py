"""
Telegram Bot: Sendet taeglich um 07:00 Uhr die Gesamtzahl der App-Installationen
(aus Supabase, Tabelle app_analytics, event_type = 'install').

Konfiguration erfolgt ueber Umgebungsvariablen (siehe unten) - so bleiben
Zugangsdaten aus dem Code heraus und koennen sicher z.B. in Railway hinterlegt
werden, ohne dass sie in einem Git-Repo landen.

Benoetigte Bibliotheken:
    pip install "python-telegram-bot[job-queue]" supabase

Start (lokal, mit Umgebungsvariablen gesetzt):
    python install_count_bot.py
"""

import logging
import os
import sys
from datetime import time
import zoneinfo

from telegram.ext import Application, ContextTypes
from supabase import create_client, Client

# -----------------------------------------------------------------------
# KONFIGURATION - aus Umgebungsvariablen gelesen
# -----------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID_RAW = os.environ.get("TELEGRAM_CHAT_ID")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

TIMEZONE = zoneinfo.ZoneInfo("Europe/Berlin")

REQUIRED_VARS = {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID_RAW,
    "SUPABASE_URL": SUPABASE_URL,
    "SUPABASE_SERVICE_ROLE_KEY": SUPABASE_SERVICE_ROLE_KEY,
}
missing = [name for name, value in REQUIRED_VARS.items() if not value]
if missing:
    sys.exit(
        "Fehlende Umgebungsvariablen: "
        + ", ".join(missing)
        + ". Bitte in Railway (oder lokal per .env) setzen."
    )

TELEGRAM_CHAT_ID = int(TELEGRAM_CHAT_ID_RAW)

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
    """Zaehlt alle Zeilen in app_analytics mit event_type = 'install'."""
    response = (
        supabase.table("app_analytics")
        .select("id", count="exact")
        .eq("event_type", "install")
        .execute()
    )
    return response.count


# -----------------------------------------------------------------------
# TAEGLICHER JOB
# -----------------------------------------------------------------------

async def send_daily_install_count(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Wird taeglich um 07:00 Uhr ausgefuehrt und sendet die Nachricht."""
    try:
        total_installs = get_total_installs()
        message = f"📊 Gesamtzahl der App-Installationen seit dem Update: {total_installs:,}".replace(",", ".")
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
        time=time(hour=14, minute=1, tzinfo=TIMEZONE),
        name="daily_install_count",
    )

    logger.info("Bot gestartet. Warte auf 07:00 Uhr taeglich...")
    application.run_polling()


if __name__ == "__main__":
    main()
