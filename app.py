from nbformat import read
from setuptools import Command
from telegram.ext.updater import Updater
from telegram.update import Update
from telegram.ext.callbackcontext import CallbackContext
from telegram.ext.commandhandler import CommandHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.ext.filters import Filters

from file_io import read_yaml

CNF = read_yaml('credentials.yaml')

updater = Updater(CNF['telegram']['bot_api_key'],
                  use_context=True)


def test(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Congrats! You've just used the test command.")


updater.dispatcher.add_handler(CommandHandler('test', test))

if __name__ == '__main__':
    updater.start_polling()
