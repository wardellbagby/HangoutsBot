# Add new /<command name> based commands in command.py
# Add any other new commands in handlers.py handle function.


# Useless function? Maybe...
import os
from hangupsbot import HangupsBot


def start():
    os.system("git pull")
    bot = HangupsBot("cookies.txt", "config.json")
    bot.run()


start()