import asyncio
from datetime import datetime
from Core.Util import UtilBot
import traceback

''' To use this, either add on to the ExtraCommands.py file or create your own Python file. Import the DispatcherSingleton
and annotate any function that you wish to be a command with the @DispatcherSingleton.register annotation, and it will
appear in the bot's help menu and be available to use.

For commands that should be hidden, use the @DispatcherSingleton.register_hidden annotation instead, and it won't
appear in the /help menu. It should be noted that hidden commands' primary purpose are to be used with autoreplies, and
won't be able to be ran by anyone other than the Bot itself.

To choose what happens when a command isn't found, register a function with @DispatcherSingleton.register_unknown, and
that function will run whenever the Bot can't find a command that suits what the user entered.'''


class NoCommandFoundError(Exception):
    pass


class CommandDispatcher(object):
    def __init__(self):
        self.commands = {}
        self.hidden_commands = {}
        self.unknown_command = None
        self.on_connect_listeners = []

    @asyncio.coroutine
    def run(self, bot, event, bot_command_char, *args, **kwds):

        bot_command_char = bot_command_char.strip()  # For cases like "/bot " or " / "

        if args[0] == bot_command_char:  # Either the command char is like "/bot" or the user did "/ ping"
            args = list(args[1:])
        if args[0].startswith(bot_command_char):
            command = args[0][len(bot_command_char):]
        else:
            command = args[0]
        try:
            func = self.commands[command]
        except KeyError:
            try:
                if event.user.is_self:
                    func = self.hidden_commands[command]
                else:
                    raise KeyError
            except KeyError:
                if self.unknown_command:
                    func = self.unknown_command
                else:
                    raise NoCommandFoundError(
                        "Command {} is not registered. Furthermore, no command found to handle unknown commands.".format
                        (command))

        func = asyncio.coroutine(func)

        args = list(args[1:])

        # For help cases.
        if len(args) > 0 and args[0] == '?':
            if func.__doc__:
                bot.send_message_segments(event.conv, UtilBot.text_to_segments(func.__doc__))
                return

        try:
            asyncio.async(func(bot, event, *args, **kwds))
        except Exception as e:
            log = open('log.txt', 'a+')
            log.writelines(str(datetime.now()) + ":\n " + traceback.format_exc() + "\n\n")
            log.close()
            print(traceback.format_exc())

    def register_aliases(self, aliases=None):
        """Registers a command under the function name & any names specified in aliases.
        """

        def func_wrapper(func):
            self.commands[func.__name__] = func
            for alias in aliases:
                self.commands[alias] = func
            return func

        return func_wrapper

    def register_extras(self, is_hidden=False, aliases=None, on_connect_listener=None):
        """Registers a function as hidden with aliases, or any combination of that."""

        def func_wrapper(func):
            if is_hidden and aliases:
                self.hidden_commands[func.__name__] = func
                for alias in aliases:
                    self.hidden_commands[alias] = func
            elif aliases:
                self.commands[func.__name__] = func
                for alias in aliases:
                    self.commands[alias] = func
            elif is_hidden:
                self.hidden_commands[func.__name__] = func
            else:
                self.commands[func.__name__] = func
            return func

        self.on_connect_listeners.append(on_connect_listener)

        return func_wrapper

    def register(self, func):
        """Decorator for registering command"""
        self.commands[func.__name__] = func
        return func

    def register_hidden(self, func):
        """Registers a command as hidden (This makes it only runnable by the Bot and it won't appear in the help menu)"""
        self.hidden_commands[func.__name__] = func
        return func

    def register_unknown(self, func):
        self.unknown_command = func
        return func

    def register_on_connect_listener(self, func):
        self.on_connect_listeners.append(func)

# CommandDispatcher singleton
DispatcherSingleton = CommandDispatcher()
