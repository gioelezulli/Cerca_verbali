import glob
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import tomllib
import os
from nc_py_api import NextcloudApp

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

# Credenziali Nextcloud
NEXTCLOUD_URL = config['nextcloud']['url']
NEXTCLOUD_USERNAME = config['nextcloud']['username']
NEXTCLOUD_PASSWORD = config['nextcloud']['password']
NEXTCLOUD_FOLDER = config['nextcloud']['folder']

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


# Funzione per connettersi a Nextcloud
def connect_to_nextcloud():
    return NextcloudApp(base_url=NEXTCLOUD_URL, user=NEXTCLOUD_USERNAME, password=NEXTCLOUD_PASSWORD)


# Funzione per cercare e scaricare file PDF da Nextcloud
def find_pdf(pdf_name):
    local_directory = os.path.join(os.path.expanduser("~"), "Desktop", "PDF_Downloads")

    # Creare la cartella sul Desktop se non esiste
    os.makedirs(local_directory, exist_ok=True)

    # Cerca il file in tutte le directory locali specificate
    for directory in PDF_DIRECTORIES:
        pattern = os.path.join(directory, '**', f"*{pdf_name}*.pdf")
        found_files = glob.glob(pattern, recursive=True)  # Cerca nelle sottocartelle
        if found_files:
            return found_files  # Restituisce una lista di file trovati

    # Se non trovato localmente, cerca su Nextcloud
    nextcloud_client = connect_to_nextcloud()

    # Cerca il file nella cartella di Nextcloud specificata
    files = nextcloud_client.files.list(NEXTCLOUD_FOLDER)
    for file_info in files:
        if pdf_name in file_info.get_name() and file_info.get_name().endswith(".pdf"):
            # Scarica il file su una cartella locale
            local_file_path = os.path.join(local_directory, file_info.get_name())
            nextcloud_client.files.download(file_info.get_path(), local_file_path)
            return [local_file_path]  # Restituisce il percorso del file scaricato

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
