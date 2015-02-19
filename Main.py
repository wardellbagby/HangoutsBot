# Add new /<command name> based commands in commands.py
# Add any other new commands in handlers.py handle function.


# Useless function? Maybe...
import os
import sys
from hangupsbot import HangupsBot


class Main:
    @staticmethod
    def start():
        # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
        os.system("git pull")
        HangupsBot("cookies.txt", "config.json").run()


if __name__ == "__main__":
    Main().start()