# /bin/bash/python
# encoding: utf-8

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import ParseMode
from util.filehandler import FileHandler
from util.database import DatabaseHandler
from util.processing import BatchProcess
from util.feedhandler import FeedHandler
import os

class RobotRss(object):

    def __init__(self, telegram_token, update_interval):

        # Initialize bot internals
        self.db = DatabaseHandler("resources/datastore.db")
        self.fh = FileHandler("..")

        # Register webhook to telegram bot
        self.updater = Updater(telegram_token)
        self.dispatcher = self.updater.dispatcher

        # Add Commands to bot
        self._addCommand(CommandHandler("rss", self.rss))
        self._addCommand(CommandHandler("stop", self.stop))
        self._addCommand(CommandHandler("how", self.how))
        self._addCommand(CommandHandler("list", self.list))
        self._addCommand(CommandHandler("about", self.about))
        self._addCommand(CommandHandler("add", self.add, pass_args=True))
        self._addCommand(CommandHandler("get", self.get, pass_args=True))
        self._addCommand(CommandHandler("remove", self.remove, pass_args=True))

        # Start the Bot
        self.processing = BatchProcess(
            database=self.db, update_interval=update_interval, bot=self.dispatcher.bot)

        self.processing.start()
        self.updater.start_polling()
        self.updater.idle()

    def _addCommand(self, command):
        """
        Registers a new command to the bot
        """

        self.updater.dispatcher.add_handler(command)

    def rss(self, bot, update):
        """
        Send a message when the command /start is issued.
        """

        telegram_user = update.message.from_user

        # Add new User if not exists
        if not self.db.get_user(telegram_id=telegram_user.id):

            message = "RSS notifikasi Telah diaktifkan, silahkan klik /how disini."
            update.message.reply_text(message)

            self.db.add_user(telegram_id=telegram_user.id,
                             username=telegram_user.username,
                             firstname=telegram_user.first_name,
                             lastname=telegram_user.last_name,
                             language_code=telegram_user.language_code,
                             is_bot=telegram_user.is_bot,
                             is_active=1)

        self.db.update_user(telegram_id=telegram_user.id, is_active=1)

        message = "silahkan klik /how disini.! untuk proses lebih lanjut!!"
        update.message.reply_text(message)

    def add(self, bot, update, args):
        """
        Adds a rss subscription to user
        """

        telegram_user = update.message.from_user

        if len(args) != 2:
            message = "Maaf! Saya tidak dapat menambahkan entri! Silakan gunakan perintah dengan memberikan argumen berikut:\n\n /add <url> <entryname> \n\n Berikut adalah contoh singkatnya: \n\n /add http:/ /www.feedforall.com/sample.xml ContohEntri"
            update.message.reply_text(message)
            return

        arg_url = FeedHandler.format_url_string(string=args[0])
        arg_entry = args[1]

        # Check if argument matches url format
        if not FeedHandler.is_parsable(url=arg_url):
            message = "Maaf! Sepertinya '" + \
                str(arg_url) + "' tidak dapat menaambahkan RSS.. Sudahkah Anda mencoba URL lain dari penyedia itu?"
            update.message.reply_text(message)
            return

        # Check if entry does not exists
        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)
        print(entries)

        if any(arg_url.lower() in entry for entry in entries):
            message = "Maaf, " + telegram_user.first_name + \
                "! Saya sudah memiliki url itu dengan tersimpan di langganan Anda. cek /list"
            update.message.reply_text(message)
            return

        if any(arg_entry in entry for entry in entries):
            message = "Maaf! Saya sudah memiliki entri dengan nama " + \
                arg_entry + " disimpan di langganan Anda.. Silakan pilih nama entri lain atau hapus entri menggunakan '/remove " + arg_entry + "'"
            update.message.reply_text(message)
            return

        self.db.add_user_bookmark(
            telegram_id=telegram_user.id, url=arg_url.lower(), alias=arg_entry)
        message = "Saya berhasil menambahkan " + arg_entry + " ke langganan Anda!"
        update.message.reply_text(message)

    def get(self, bot, update, args):
        """
        Manually parses an rss feed
        """

        telegram_user = update.message.from_user

        if len(args) > 2:
            message = "Untuk mendapatkan berita terakhir dari langganan Anda, silakan gunakan /get <entryname> [optional: <count 1-10>]. Pastikan Anda menambahkan feed terlebih dahulu menggunakan perintah /add."
            update.message.reply_text(message)
            return

        if len(args) == 2:
            args_entry = args[0]
            args_count = int(args[1])
        else:
            args_entry = args[0]
            args_count = 4

        url = self.db.get_user_bookmark(
            telegram_id=telegram_user.id, alias=args_entry)

        if url is None:
            message = "Saya tidak dapat menemukan entri dengan label " + \
                args_entry + " di langganan Anda! Silakan periksa langganan Anda menggunakan /list dan gunakan perintah hapus lagi!"
            update.message.reply_text(message)
            return

        entries = FeedHandler.parse_feed(url[0], args_count)
        for entry in entries:
            message = "UPDATE ❗: " + entry.title + " \nINFO LEBIH LANJUT : <a href='" + \
                entry.link + "'>Klik disini</a> \n\nNotifikasi Dari - " + url[1] + " | @ccgnimex_bot" 
            print(message)
            try:
                update.message.reply_text(message, parse_mode=ParseMode.HTML)
            except Unauthorized:
                self.db.update_user(telegram_id=telegram_user.id, is_active=0)
            except TelegramError:
                # handle all other telegram related errors
                pass

    def remove(self, bot, update, args):
        """
        Removes an rss subscription from user
        """

        telegram_user = update.message.from_user

        if len(args) != 1:
            message = "Untuk menghapus langganan dari daftar Anda, gunakan /remove <entryname>. Untuk melihat semua langganan Anda beserta nama entrinya, gunakan /list !"
            update.message.reply_text(message)
            return

        entry = self.db.get_user_bookmark(
            telegram_id=telegram_user.id, alias=args[0])

        if entry:
            self.db.remove_user_bookmark(
                telegram_id=telegram_user.id, url=entry[0])
            message = "Saya Menghapus " + args[0] + " dari daftar RSS"
            update.message.reply_text(message)
        else:
            message = "Saya tidak dapat menemukan entri dengan label " + \
                args[0] + " di langganan Anda! Silakan periksa langganan Anda menggunakan /list dan gunakan perintah hapus lagi!"
            update.message.reply_text(message)

    def list(self, bot, update):
        """
        Displays a list of all user subscriptions
        """

        telegram_user = update.message.from_user

        message = "Berikut adalah daftar semua langganan yang saya simpan untuk Anda!"
        update.message.reply_text(message)

        entries = self.db.get_urls_for_user(telegram_id=telegram_user.id)

        for entry in entries:
            message = "[" + entry[1] + "]\n " + entry[0]
            update.message.reply_text(message)

    def how(self, bot, update):
        """
        Send a message when the command /help is issued.
        """

        message = "gunakan /help bruh..."
        update.message.reply_text(message, parse_mode=ParseMode.HTML)

    def stop(self, bot, update):
        """
        Stops the bot from working
        """

        telegram_user = update.message.from_user
        self.db.update_user(telegram_id=telegram_user.id, is_active=0)

        message = "Oh.. Oke, saya tidak akan mengirimi Anda pembaruan berita lagi! Jika Anda berubah pikiran dan ingin menerima pesan dari saya lagi, gunakan perintah /rss lagi!"
        update.message.reply_text(message)

    def about(self, bot, update):
        """
        Shows about information
        """

        message = "Thank you for using <b>RobotRSS</b>! \n\n If you like the bot, please recommend it to others! \n\nDo you have problems, ideas or suggestions about what the bot should be able to do? Then contact my developer <a href='http://cbrgm.de'>@cbrgm</a> or create an issue on <a href='https://github.com/cbrgm/telegram-robot-rss'>Github</a>. There you will also find my source code, if you are interested in how I work!"
        update.message.reply_text(message, parse_mode=ParseMode.HTML)


if __name__ == '__main__':
    # Load Credentials
    fh = FileHandler("..")
    credentials = fh.load_json("resources/credentials.json")

    if 'BOT_TOKEN' in os.environ:
        token = os.environ.get("BOT_TOKEN")
    else:
        token = credentials["telegram_token"]
    if 'UPDATE_INTERVAL' in os.environ:
        update = int(os.environ.get("UPDATE_INTERVAL", 100))
    else:
        update = credentials["update_interval"]

    RobotRss(telegram_token=token, update_interval=update)
