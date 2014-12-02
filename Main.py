# Add new /<command name> based commands in commands.py
# Add any other new commands in handlers.py handle function.


# Useless function? Maybe...
import os
from hangupsbot import HangupsBot


class Main:
    bot = None

    @staticmethod
    def start():
        # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
        os.system("git pull")
        if Main.bot is not None:
            Main.bot.stop()
        Main.bot = HangupsBot("cookies.txt", "config.json")
        Main.bot.run()


Main().start()