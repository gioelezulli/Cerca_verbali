from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import tomllib
import os
import nc_py_api
import tempfile
from telegram.constants import ChatAction

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
AUTHORIZED_USERS = config['authorization']['authorized_users']
TEMP_DIR = config['temp_dir1']['cartella_temporanea']
# Credenziali Nextcloud
NEXTCLOUD_URL = config['nextcloud']['url']
NEXTCLOUD_USERNAME = config['nextcloud']['username']
NEXTCLOUD_PASSWORD = config['nextcloud']['password']
NEXTCLOUD_FOLDER = config['nextcloud']['folder']

# Funzione per controllare se l'utente è autorizzato
def is_authorized(user_id):
    return user_id in AUTHORIZED_USERS

if __name__ == "__main__":

    # Replace these values with your Nextcloud URL, username, and password (app password)
    nextcloud_url = NEXTCLOUD_URL
    username = NEXTCLOUD_USERNAME
    password = NEXTCLOUD_PASSWORD  # Use an app-specific password for security

    # Initialize the NextCloud client
    nc = nc_py_api.Nextcloud(nextcloud_url=nextcloud_url, nc_auth_user=username, nc_auth_pass=password)

    # Lista delle cartelle in cui concentrarsi per la ricerca
    cartelle = NEXTCLOUD_FOLDER


    # Funzione per cercare i file in Nextcloud e scaricarli
    def search_and_download_files(partial_name):
        files_to_download = []

        # Verifica se la directory esiste, se no creala
        if not os.path.exists(TEMP_DIR):
            try:
                os.makedirs(TEMP_DIR)
                print(f"Creata la directory: {TEMP_DIR}")
            except Exception as e:
                print(f"Errore nella creazione della directory principale: {str(e)}")
                return None, None

        # Crea una cartella temporanea nella directory specificata da TEMP_DIR
        try:
            temp_dir = tempfile.mkdtemp(prefix="temp_nextcloud_files_", dir=TEMP_DIR)
            print(f"Cartella temporanea creata: {temp_dir}")
        except Exception as e:
            print(f"Errore nella creazione della cartella temporanea: {str(e)}")
            return None, None


        for folder in NEXTCLOUD_FOLDER:
            result = nc.files.find(["like", "name", f"%{partial_name}%.pdf"], path=folder)  # Cerca solo PDF
            for file in result:
                file_name = file.name
                file_path = file.user_path
                local_file_path = os.path.join(temp_dir, file_name)
                nc.files.download2stream(file_path, local_file_path)
                files_to_download.append(local_file_path)  # Aggiungi il percorso locale del file alla lista

        return files_to_download, temp_dir


    # Comando /start
    async def start_command(update: Update, context):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        await update.message.reply_text("Ciao! Inviami il nome del file PDF che stai cercando.")


    # Funzione per la ricerca e invio dei file via bot
    async def search_pdf(update: Update, context):
        user_id = update.effective_user.id
        if user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("Non sei autorizzato a usare questo bot.")
            return

        query = update.message.text.strip()
        if not query:
            await update.message.reply_text("Inserisci una chiave di ricerca.")
            return

        await update.message.reply_text(f"Cerco i file contenenti '{query}'...")
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        try:
            # Cerca e scarica i file
            files_found, temp_dir = search_and_download_files(query)

            # Controllo se la cartella temporanea è stata creata correttamente
            if temp_dir is None:
                await update.message.reply_text("Errore nella creazione della cartella temporanea. Riprova più tardi.")
                return

            if not files_found:
                await update.message.reply_text("Non ho trovato nessun file.")
            else:
                for file_path in files_found:
                    with open(file_path, 'rb') as file:
                        await update.message.reply_document(file)
                await update.message.reply_text("File trovati e inviati con successo!")

        except Exception as e:
            await update.message.reply_text(f"Errore durante la ricerca o il download: {str(e)}")
        finally:
            # Pulisci la cartella temporanea
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)


    # Configura il bot
    def main():
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Comandi del bot
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_pdf))

        # Avvia il bot
        application.run_polling()


    if __name__ == "__main__":
        main()