import logging, shlex, unicodedata, asyncio
from cleverbot import ChatterBotFactory, ChatterBotType
import hangups

from commands import command

words = open("wordlist.txt")
list = []
for line in words:
    list.append(line.strip('\n'))


class MessageHandler(object):
    """Handle Hangups conversation events"""
    cleversession = -1
    dotalk = False

    def __init__(self, bot, bot_command='/'):
        self.bot = bot
        self.bot_command = bot_command
        from BotCommands import BotCommands

        self.commands = BotCommands()
        factory = ChatterBotFactory()
        cleverbotter = factory.create(ChatterBotType.CLEVERBOT)
        MessageHandler.cleversession = cleverbotter.create_session()

    @staticmethod
    def shutup(bot, event):
        if bot.conv_settings[event.conv_id] is None:
            bot.conv_settings[event.conv_id] = {}
        settings = dict(bot.conv_settings[event.conv_id])
        settings['clever'] = False
        bot.conv_settings[event.conv_id] = settings

    @staticmethod
    def speakup(bot, event):
        if MessageHandler.cleversession is None:
            factory = ChatterBotFactory()
            cleverbotter = factory.create(ChatterBotType.CLEVERBOT)
            MessageHandler.cleversession = cleverbotter.create_session()

        if bot.conv_settings[event.conv_id] is None:
            bot.conv_settings[event.conv_id] = {}
        settings = dict(bot.conv_settings[event.conv_id])
        settings['clever'] = True
        bot.conv_settings[event.conv_id] = settings


    @staticmethod
    def word_in_text(word, text):
        """Return True if word is in text"""
        # Transliterate unicode characters to ASCII and make everything lowercase
        word = unicodedata.normalize('NFKD', word).encode('ascii', 'ignore').decode().lower()
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode().lower()

        # Replace delimiters in text with whitespace
        for delim in '.,:;!?':
            text = text.replace(delim, ' ')

        return True if word in text.split() else False

    @asyncio.coroutine
    def handle(self, event):
        # Use this to add commands that are based off of what text the user inputs when it isn't a command.
        if event.conv_id not in self.bot.conv_settings:
            self.bot.conv_settings[event.conv_id] = {}
        try:
            muted = self.bot.conv_settings[event.conv_id]['muted']
        except KeyError:
            muted = False
            import commands

            commands.unmute(self.bot, event)
        try:
            clever = self.bot.conv_settings[event.conv_id]['clever']
        except KeyError:
            clever = False
            import commands

            commands.shutup(self.bot, event)

        textuppers = str(event.text).upper()
        if not event.user.is_self and not event.text.startswith('/'):
            from UtilBot import UtilBot

            if event.text[0] == '#':
                self.bot.send_message(event.conv, self.commands.unhashtag(str(event.text)))
            elif UtilBot.is_haiku(textuppers):
                segments = [hangups.ChatMessageSegment('Haiku: ', is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
                lines = UtilBot.convert_to_haiku(textuppers).split('\n')
                for line in lines:
                    segments.append(hangups.ChatMessageSegment(line))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.pop()
                self.bot.send_message_segments(event.conv, segments)
            elif "🚮" in str(event.text):
                self.bot.send_message(event.conv, "🚮")
            elif textuppers.endswith('?!'):
                self.bot.send_message(event.conv, "I agree with " + str(event.user.full_name) + '.')
            elif "AMERICA" in str(event.text).upper():
                self.bot.send_message(event.conv, "MURICA!!!!!!!")
            elif "MURICA" in str(event.text).upper():
                self.bot.send_message(event.conv, "Fuck yeah!")
            elif not muted:
                if (clever or (
                        self.commands.nameregex.search(textuppers))) and MessageHandler.cleversession is not None:
                    self.bot.send_message(event.conv, MessageHandler.cleversession.think(str(event.text[5:])))

        """Handle conversation event"""
        if logging.root.level == logging.DEBUG:
            event.print_debug()

        if not event.user.is_self and event.text:
            if event.text.startswith('/'):
                # Run command
                if event.text[1] == '?':
                    event.text = "/help"
                yield from self.handle_command(event)
            else:
                # Forward messages
                yield from self.handle_forward(event)

                # Send automatic replies
                yield from self.handle_autoreply(event)

    @asyncio.coroutine
    def handle_command(self, event):
        """Handle command messages"""
        # Test if command handling is enabled
        if not self.bot.get_config_suboption(event.conv_id, 'commands_enabled'):
            return

        # Parse message
        line_args = shlex.split(event.text, posix=False)
        i = 0
        while i < len(line_args):
            line_args[i] = line_args[i].strip()
            if line_args[i] == '' or line_args[i] == '':
                line_args.remove(line_args[i])
            else:
                i += 1


        # Test if command length is sufficient
        if len(line_args) < 1:
            self.bot.send_message(event.conv,
                                  '{}: Not a valid command.'.format(event.user.full_name))
            return

        # Test if user has permissions for running command
        commands_admin_list = self.bot.get_config_suboption(event.conv_id, 'commands_admin')
        if commands_admin_list and line_args[0].lower().replace('/', '') in commands_admin_list:
            admins_list = self.bot.get_config_suboption(event.conv_id, 'admins')
            if event.user_id.chat_id not in admins_list:
                if not self.bot.dev:
                    self.bot.send_message(event.conv,
                                          '{}: I\'m sorry, Dave. I\'m afraid I can\'t do that.'.format(
                                              event.user.full_name))
                return

        # Run command
        yield from command.run(self.bot, event, *line_args[0:])

    @asyncio.coroutine
    def handle_forward(self, event):
        # Test if message forwarding is enabled
        if not self.bot.get_config_suboption(event.conv_id, 'forwarding_enabled'):
            return

        forward_to_list = self.bot.get_config_suboption(event.conv_id, 'forward_to')
        if forward_to_list:
            for dst in forward_to_list:
                try:
                    conv = self.bot._conv_list.get(dst)
                except KeyError:
                    continue

                # Prepend forwarded message with name of sender
                link = 'https://plus.google.com/u/0/{}/about'.format(event.user_id.chat_id)
                segments = [hangups.ChatMessageSegment(event.user.full_name, hangups.SegmentType.LINK,
                                                       link_target=link, is_bold=True),
                            hangups.ChatMessageSegment(': ', is_bold=True)]
                # Copy original message segments
                segments.extend(event.conv_event.segments)
                # Append links to attachments (G+ photos) to forwarded message
                if event.conv_event.attachments:
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                    segments.extend([hangups.ChatMessageSegment(link, hangups.SegmentType.LINK, link_target=link)
                                     for link in event.conv_event.attachments])
                self.bot.send_message_segments(conv, segments)

    @asyncio.coroutine
    def handle_autoreply(self, event):
        """Handle autoreplies to keywords in messages"""
        # Test if autoreplies are enabled
        if not self.bot.get_config_suboption(event.conv_id, 'autoreplies_enabled'):
            return

        autoreplies_list = self.bot.get_config_suboption(event.conv_id, 'autoreplies')
        if autoreplies_list:
            for kwds, sentence in autoreplies_list:
                for kw in kwds:
                    if self.word_in_text(kw, event.text) or kw == "*":
                        self.bot.send_message(event.conv, sentence)
                        break
