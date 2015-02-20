import asyncio
from datetime import datetime
import traceback

''' To use this, either add on to the ExtraCommands.py file or create your own Python file. Import the DispatcherSingleton
and annotate any function that you wish to be a command with the @DispatcherSingleton.register annotation, and it will
appear in the bot's help menu and be available to use.

For commands that should be hidden, use the @DispatcherSingleton.register_hidden annotation instead, and it won't
appear in the /help menu.

To choose what happens when a command isn't found, register a function with @DispatcherSingleton.register_unknown, and
that function will run whenever the Bot can't find a command that suits what the user entered.'''


class CommandDispatcher(object):

    def __init__(self):
        self.commands = {}
        self.hidden_commands = {}
        self.unknown_command = None

    @asyncio.coroutine
    def run(self, bot, event, *args, **kwds):
        if args[0].startswith('/'):
            command = args[0][1:]
        else:
            command = args[0]
        try:
            func = self.commands[command]
        except KeyError:
            try:
                func = self.hidden_commands[command]
            except KeyError:
                if self.unknown_command:
                    func = self.unknown_command
                else:
                    raise

        func = asyncio.coroutine(func)

        args = list(args[1:])

        try:
            yield from func(bot, event, *args, **kwds)
        except Exception as e:
            log = open('log.txt', 'a+')
            log.writelines(str(datetime.now()) + ":\n " + traceback.format_exc() + "\n\n")
            log.close()
            print(traceback.format_exc())

    def register(self, func):
        """Decorator for registering command"""
        self.commands[func.__name__] = func
        return func

    def register_hidden(self, func):
        self.hidden_commands[func.__name__] = func
        return func

    def register_unknown(self, func):
        self.unknown_command = func
        return func

# CommandDispatcher singleton
DispatcherSingleton = CommandDispatcher()