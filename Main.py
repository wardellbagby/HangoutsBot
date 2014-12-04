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
        # Main.bot = HangupsBot("cookies.txt", "config.json")

        index = -1
        for x in range(sys.argv):
            if isinstance(sys.argv[x], dict):
                if sys.argv[x]["isSettings"]:
                    index = x

        if index != -1:
            settings = sys.argv[index]
        else:
            settings = {}
            sys.argv.append(settings)
            index = len(sys.argv)-1
            settings["isSettings"] = True
            settings[index]["bot"] = None
            settings[index]["event"] = None

        if settings["bot"] is None:
            Main.bot = HangupsBot("cookies.txt", "config.json")
            settings["bot"] = Main.bot
        else:
            Main.bot = settings["bot"]
            if settings["event"] is not None:
                Main.bot.send_message(settings["event"].conv, "Hello world")
                
        sys.argv[index] = settings
        Main.bot.run()


Main().start()