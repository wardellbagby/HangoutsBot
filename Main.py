# Add new /<command name> based commands in commands.py
# Add any other new commands in Handlers.py handle function.


# Useless function? Maybe...
import os

from Core.Bot import HangoutsBot


class Main:
    @staticmethod
    def start():
        # This commands auto updates the project. Please have Git installed and in your PATH variable on Windows.
        os.system("git pull")
        HangoutsBot("Core" + os.sep + "cookies.txt", "Core" + os.sep + "config.json").run()


if __name__ == "__main__":
    Main().start()