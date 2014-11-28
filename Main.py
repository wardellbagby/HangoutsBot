# Add new /<command name> based commands in commands.py
# Add any other new commands in handlers.py handle function.


# Useless function? Maybe...
import os
from hangupsbot import HangupsBot


def start():
    # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
    os.system("git pull")
    bot = HangupsBot("cookies.txt", "config.json")
    bot.run()


start()