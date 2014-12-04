# Add new /<command name> based commands in commands.py
# Add any other new commands in handlers.py handle function.


# Useless function? Maybe...
import os
import sys
from hangupsbot import HangupsBot


class Main:
    bot = None

    @staticmethod
    def start():
        # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
        os.system("git pull")
        if len(sys.argv) > 1 and sys.argv[1] is not None:
            Main.bot = sys.argv[1]
        if Main.bot is not None:
            Main.bot.stop()
        if sys.argv["bot"] is None:
            Main.bot = HangupsBot("cookies.txt", "config.json")
        else:
            Main.bot = sys.argv["bot"]
            if sys["event"] is not None:
                Main.bot.send_message(sys["event"].conv, "Hello world")
        Main.bot.run()


Main().start()