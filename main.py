import os
import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import tomllib
import os


def load_config():
    # Definisce il percorso del file di configurazione
    config_path = os.path.join(os.path.dirname(__file__), 'Config', 'config.toml')

    # Legge il file config.toml usando tomllib
    with open(config_path, 'rb') as config_file:
        config = tomllib.load(config_file)

    return config


# Esempio di utilizzo della configurazione caricata
config = load_config()

TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']
PDF_DIRECTORIES = config['directories']['pdf_directories']
AUTHORIZED_USERS = config['authorization']['authorized_users']


# Funzione per controllare se l'utente è autorizzato
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS


async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return
        # Usa 'await' per chiamare il metodo asincrono
    await update.message.reply_text("Ciao! Inviami il nome del file PDF che stai cercando.")


def find_pdf(pdf_name):
    # Cerca il file in tutte le directory specificate
    for directory in PDF_DIRECTORIES:
        # Cerca file PDF che contengono il nome cercato, ignorando maiuscole/minuscole
        pattern = os.path.join(directory, '**', f"*{pdf_name}*.pdf")
        found_files = glob.glob(pattern, recursive=True)  # Usa recursive=True per cercare anche nelle sottocartelle
        if found_files:
            return found_files  # Restituisce una lista di file trovati
    return None


async def search_pdf(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id

    if not is_authorized(user_id):
        await update.message.reply_text("Non sei autorizzato a usare questo bot.")
        return

    # Ottieni il testo inviato dall'utente
    query = update.message.text.strip()

    # Cerca i PDF con il nome specificato
    found_files = find_pdf(query)

    if found_files:
        for file in found_files:
            # Manda il file trovato come documento (usa 'await')
            await update.message.reply_document(document=open(file, 'rb'))
    else:
        # Usa 'await' per chiamare il metodo asincrono
        await update.message.reply_text("Nessun file trovato con questo nome.")


async def start_command(update: Update, context: CallbackContext):
    await start(update, context)


async def search_command(update: Update, context: CallbackContext):
    await search_pdf(update, context)


def main() -> None:
    # Crea l'applicazione del bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Comando /start
    application.add_handler(CommandHandler("start", start_command))

    # Gestione del testo inviato dall'utente (ricerca PDF)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_command))

    # Avvia il bot
    application.run_polling()


if __name__ == '__main__':
    main()
