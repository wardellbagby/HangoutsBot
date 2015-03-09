import json
from urllib import parse
from urllib import request
import re

from bs4 import BeautifulSoup
import hangups
from hangups.ui.utils import get_conv_name

from Libraries.cleverbot import ChatterBotFactory, ChatterBotType
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot


clever_session = ChatterBotFactory().create(ChatterBotType.CLEVERBOT).create_session()
last_recorded, last_recorder = None, None
voted = {}
vote_subject = None
vote_callback = None


@DispatcherSingleton.register_unknown
def unknown_command(bot, event, *args):
    bot.send_message(event.conv,
                     '{}: Unknown command!'.format(event.user.full_name))


@DispatcherSingleton.register_hidden
def think(bot, event, *args):
    if clever_session:
        bot.send_message(event.conv, clever_session.think(' '.join(args)))


@DispatcherSingleton.register
def help(bot, event, *args):
    segments = [hangups.ChatMessageSegment('Current implemented commands:', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(', '.join(sorted(DispatcherSingleton.commands.keys()))),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Use: /<command name> ? to find more information about the command.')]
    bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def devmode(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Development Mode', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /devmode <on|off>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: When development mode is on, all outputted text will go to the Python console instead of the Hangouts chat.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if ''.join(args) == "on":
            bot.dev = True
        else:
            bot.dev = False


@DispatcherSingleton.register
def define(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Define', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /define <word to search for> <optional: definition number [defaults to 1] OR * to show all definitions>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /define <word to search for> <start index and end index in form of int:int (e.g., /define test 1:3)>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Show definitions for a word.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if args[-1].isdigit():
            definition, length = UtilBot.define(' '.join(args[0:-1]), num=int(args[-1]))
            segments = [hangups.ChatMessageSegment(' '.join(args[0:-1]).title(), is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(
                            definition.replace('\n', ''))]
            bot.send_message_segments(event.conv, segments)
        elif args[-1] == '*':
            args = list(args)
            args[-1] = '1:*'
        if ':' in args[-1]:
            start, end = re.split(':', args[-1])
            try:
                start = int(start)
            except ValueError:
                start = 1
            display_all = False
            if end == '*':
                end = 100
                display_all = True
            else:
                try:
                    end = int(end)
                except ValueError:
                    end = 3
            if start < 1:
                start = 1
            if start > end:
                end, start = start, end
            if start == end:
                end += 1
            if len(args) <= 1:
                bot.send_message(event.conv, "Invalid usage for /define.")
                return
            query = ' '.join(args[:-1])
            definition_segments = [hangups.ChatMessageSegment(query.title(), is_bold=True),
                                   hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK)]
            if start < end:
                x = start
                while x <= end:
                    definition, length = UtilBot.define(query, num=x)
                    definition_segments.append(hangups.ChatMessageSegment(definition))
                    if x != end:
                        definition_segments.append(
                            hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK))
                        definition_segments.append(
                            hangups.ChatMessageSegment('', segment_type=hangups.SegmentType.LINE_BREAK))
                    if end > length:
                        end = length
                    if display_all:
                        end = length
                        display_all = False
                    x += 1
                bot.send_message_segments(event.conv, definition_segments)
            return
        else:
            args = list(args)
            args.append("1:3")
            define(bot, event, *args)
            return


@DispatcherSingleton.register
def wiki(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Wikipedia', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /wiki <keyword to search for> <optional: sentences to display [defaults to 3]>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Get summary from Wikipedia on search parameter.')]
        bot.send_message_segments(event.conv, segments)
    else:
        from wikipedia import wikipedia, PageError, DisambiguationError

        def summary(self, sentences=3):
            if not getattr(self, '_summary', False):
                query_params = {
                    'prop': 'extracts',
                    'explaintext': '',
                    'exintro': '',
                }
            query_params['exsentences'] = sentences
            if not getattr(self, 'title', None) is None:
                query_params['titles'] = self.title
            else:
                query_params['pageids'] = self.pageid

            request = wikipedia._wiki_request(query_params)
            self._summary = request['query']['pages'][self.pageid]['extract']

            return self._summary

        wikipedia.WikipediaPage.summary = summary
        try:
            sentences = 3
            try:
                if args[-1].isdigit():
                    sentences = args[-1]
                    args = args[:-1]
                page = wikipedia.page(' '.join(args))
            except DisambiguationError as e:
                page = wikipedia.page(wikipedia.search(e.options[0], results=1)[0])
            segments = [
                hangups.ChatMessageSegment(page.title, hangups.SegmentType.LINK, is_bold=True, link_target=page.url),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(page.summary(sentences=sentences))]

            bot.send_message_segments(event.conv, segments)
        except PageError:
            bot.send_message(event.conv, "Couldn't find \"{}\". Try something else.".format(' '.join(args)))


@DispatcherSingleton.register
def goog(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Google', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /goog <optional: search parameter>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Get the first result from Google\'s search using search parameter.')]
        bot.send_message_segments(event.conv, segments)
    else:
        search_terms = " ".join(args)
        if search_terms == "" or search_terms == " ":
            search_terms = "google"
        query = parse.urlencode({'q': search_terms})
        url = 'https://www.google.com/search?%s&btnI=1' \
              % query
        headers = {
            'User-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'}
        req = request.Request(url, None, headers)
        resp = request.urlopen(req)
        soup = BeautifulSoup(resp)

        bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Result:', is_bold=True),
                                               hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                                               hangups.ChatMessageSegment(soup.title.string, hangups.SegmentType.LINK,
                                                                          link_target=url)])


@DispatcherSingleton.register
def ping(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Ping', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /ping'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Easy way to check if Bot is running.')]
        bot.send_message_segments(event.conv, segments)
    else:
        bot.send_message(event.conv, 'pong')


@DispatcherSingleton.register
def echo(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Echo', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /echo <text to echo>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Bot will reply with whatever text is inputted exactly, minus the /echo command.')]
        bot.send_message_segments(event.conv, segments)
    else:
        bot.send_message(event.conv, '{}'.format(' '.join(args)))


@DispatcherSingleton.register
def users(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Users', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /users'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Listing all users in the current hangout (including G + accounts and emails)')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('Users: '.format(len(event.conv.users)),
                                               is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
        for user in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
            link = 'https://plus.google.com/u/0/{}/about'.format(user.id_.chat_id)
            segments.append(hangups.ChatMessageSegment(user.full_name, hangups.SegmentType.LINK,
                                                       link_target=link))
            if user.emails:
                segments.append(hangups.ChatMessageSegment(' ('))
                segments.append(hangups.ChatMessageSegment(user.emails[0], hangups.SegmentType.LINK,
                                                           link_target='mailto:{}'.format(user.emails[0])))
                segments.append(hangups.ChatMessageSegment(')'))

            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def user(bot, event, username, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('User', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /user <user name>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: List information about user.)')]
        bot.send_message_segments(event.conv, segments)
    else:
        username_lower = username.strip().lower()
        segments = [hangups.ChatMessageSegment('User: "{}":'.format(username),
                                               is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
        for u in sorted(bot._user_list._user_dict.values(), key=lambda x: x.full_name.split()[-1]):
            if not username_lower in u.full_name.lower():
                continue

            link = 'https://plus.google.com/u/0/{}/about'.format(u.id_.chat_id)
            segments.append(hangups.ChatMessageSegment(u.full_name, hangups.SegmentType.LINK,
                                                       link_target=link))
            if u.emails:
                segments.append(hangups.ChatMessageSegment(' ('))
                segments.append(hangups.ChatMessageSegment(u.emails[0], hangups.SegmentType.LINK,
                                                           link_target='mailto:{}'.format(u.emails[0])))
                segments.append(hangups.ChatMessageSegment(')'))
            segments.append(hangups.ChatMessageSegment(' ... {}'.format(u.id_.chat_id)))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def hangouts(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Hangouts', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /hangouts'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: List all Hangouts this Bot is currently in, along with what settings those Hangouts are using.')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('Currently In These Hangouts:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
        for c in bot.list_conversations():
            s = '{} [commands: {:d}, forwarding: {:d}, autoreplies: {:d}]'.format(get_conv_name(c, truncate=True),
                                                                                  bot.get_config_suboption(c.id_,
                                                                                                           'commands_enabled'),
                                                                                  bot.get_config_suboption(c.id_,
                                                                                                           'forwarding_enabled'),
                                                                                  bot.get_config_suboption(c.id_,
                                                                                                           'autoreplies_enabled'))
            segments.append(hangups.ChatMessageSegment(s))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))

        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def rename(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Rename', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /rename <new title>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Changes the chat title of the room.')]
        bot.send_message_segments(event.conv, segments)
    else:
        yield from bot._client.setchatname(event.conv_id, ' '.join(args))


@DispatcherSingleton.register
def leave(bot, event, conversation=None, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Leave', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /leave'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Leaves the chat room.')]
        bot.send_message_segments(event.conv, segments)
    else:
        convs = []
        if not conversation:
            convs.append(event.conv)
        else:
            conversation = conversation.strip().lower()
            for c in bot.list_conversations():
                if conversation in get_conv_name(c, truncate=True).lower():
                    convs.append(c)

        for c in convs:
            yield from c.send_message([
                hangups.ChatMessageSegment('I\'ll be back!')
            ])
            yield from bot._conv_list.leave_conversation(c.id_)


@DispatcherSingleton.register
def clear(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Clear', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /clear'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Clears the current screen.')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Intentionally not displayed.', hangups.SegmentType.LINE_BREAK)]
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def mute(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Mute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /mute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Mutes all non-command replies.')]
        bot.send_message_segments(event.conv, segments)
    else:
        try:
            bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = False
        except KeyError:
            bot.config['conversation'][event.conv_id] = {}
            bot.config['conversation'][event.conv_id]['autoreplies_enabled'] = False
        bot.config.save()


@DispatcherSingleton.register
def unmute(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Unmute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /unmute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Unmutes all non-command replies.')]
        bot.send_message_segments(event.conv, segments)
    else:
        try:
            bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = True
        except KeyError:
            bot.config['conversations'][event.conv_id] = {}
            bot.config['conversations'][event.conv_id]['autoreplies_enabled'] = True
        bot.config.save()


@DispatcherSingleton.register
def status(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Status', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /status'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Shows current relevant Bot settings.')]
        bot.send_message_segments(event.conv, segments)
    else:

        segments = [hangups.ChatMessageSegment('Status:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Autoreplies: ' + ('Enabled' if bot.config['conversations'][event.conv_id][
                            'autoreplies_enabled'] else 'Disabled'))]
        bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def reload(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Reload', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /reload'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Reloads current config file.')]
        bot.send_message_segments(event.conv, segments)
    else:
        bot.config.load()


@DispatcherSingleton.register
def quit(bot, event, *args):
    print('HangupsBot killed by user {} from conversation {}'.format(event.user.full_name,
                                                                     get_conv_name(event.conv, truncate=True)))
    yield from bot._client.disconnect()


@DispatcherSingleton.register
def config(bot, event, cmd=None, *args):
    if cmd == 'get' or cmd is None:
        config_args = list(args)
        value = bot.config.get_by_path(config_args) if config_args else dict(bot.config)
    elif cmd == 'set':
        config_args = list(args[:-1])
        if len(args) >= 2:
            bot.config.set_by_path(config_args, json.loads(args[-1]))
            bot.config.save()
            value = bot.config.get_by_path(config_args)
        else:
            yield from DispatcherSingleton.unknown_command(bot, event)
            return
    else:
        yield from DispatcherSingleton.unknown_command(bot, event)
        return

    if value is None:
        value = 'Parameter does not exist!'

    config_path = ' '.join(k for k in ['config'] + config_args)
    segments = [hangups.ChatMessageSegment('{}:'.format(config_path),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    segments.extend(UtilBot.text_to_segments(json.dumps(value, indent=2, sort_keys=True)))
    bot.send_message_segments(event.conv, segments)


@DispatcherSingleton.register
def block(bot, event, username=None, *args):
    if not username:
        segments = [hangups.ChatMessageSegment("Blocked Users: ", is_bold=True),
                    hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment("No users blocked.")]
        if len(UtilBot.get_blocked_users_in_conversations(event.conv_id)) > 0:
            segments.pop()
            for user in event.conv.users:
                if UtilBot.is_user_blocked(event.conv_id, user.id_):
                    segments.append(hangups.ChatMessageSegment(user.full_name))
                    segments.append(hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK))
            segments.pop()
        bot.send_message_segments(event.conv, segments)
        return
    username_lower = username.strip().lower()
    for u in sorted(event.conv.users, key=lambda x: x.full_name.split()[-1]):
        if not username_lower in u.full_name.lower() or event.user.is_self:
            continue

        if UtilBot.is_user_blocked(event.conv_id, u.id_):
            UtilBot.remove_from_blocklist(event.conv_id, u.id_)
            bot.send_message(event.conv, "Unblocked User: {}".format(u.full_name))
            return
        UtilBot.add_to_blocklist(event.conv_id, u.id_)
        bot.send_message(event.conv, "Blocked User: {}".format(u.full_name))
        return


@DispatcherSingleton.register
def vote(bot, event, set_vote=None, *args):
    if set_vote == '?':
        segments = [hangups.ChatMessageSegment('Vote', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote <subject to vote on>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote <yea|yes|for|nay|no|against (used to cast a vote)>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote cancel'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote abstain'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /vote'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /vote admin (used to start a vote for a new conversation admin)'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Starts a vote in which a 50% majority wins.')]
        bot.send_message_segments(event.conv, segments)
    else:
        global vote_subject, vote_callback, voted

        # Removes user from having to vote.
        if set_vote is not None and set_vote.lower() == 'abstain':
            if vote_subject is not None and voted is not None:
                bot.send_message(event.conv, 'User {} has abstained from voting.'.format(event.user.full_name))
                del voted[event.user.full_name]
            else:
                bot.send_message(event.conv, 'No vote currently in process to abstain from.')

            # Check if the vote has ended
            true_count = list(voted.values()).count(True)
            false_count = list(voted.values()).count(False)
            total = len(voted.values())
            if float(true_count) / float(total) > .5:
                for key in voted.keys():
                    voted[key] = True
            elif float(false_count) / float(total) > .5:
                for key in voted.keys():
                    voted[key] = False
            if not (None in voted.values()):
                yeas = 0
                nahs = 0
                for set_vote in voted.values():
                    if set_vote:
                        yeas += 1
                    else:
                        nahs += 1
                if yeas != nahs:
                    bot.send_message(event.conv,
                                     'In the matter of: "' + vote_subject + '", the ' + (
                                         'Yeas' if yeas > nahs else 'Nays') + ' have it.')
                else:
                    bot.send_message(event.conv, "The vote ended in a tie in the matter of: {}".format(vote_subject))
                if vote_callback is not None:
                    vote_callback(yeas > nahs)
                vote_subject = None
                voted = None
            return

        # Cancels the vote
        if set_vote is not None and set_vote.lower() == "cancel":
            if vote_subject is not None and voted is not None:
                bot.send_message(event.conv, 'Vote "{}" cancelled.'.format(vote_subject))
                vote_subject = None
                voted = None
            else:
                bot.send_message(event.conv, 'No vote currently in process.')
            return

        # Stats a new vote
        if vote_subject is None and set_vote is not None:
            vote_subject = set_vote + ' ' + ' '.join(args)
            if vote_subject.lower().strip() == "admin":  # For the special Conversation Admin case.

                vote_subject = '{} for Conversation Admin for chat {}'.format(event.user.full_name,
                                                                              get_conv_name(event.conv))

                def set_conv_admin(won):
                    if won:
                        try:
                            bot.config["conversations"][event.conv_id]["conversation_admin"] = event.user.id_[0]
                        except (KeyError, TypeError):
                            bot.config["conversations"][event.conv_id] = {}
                            bot.config["conversations"][event.conv_id]["admin"] = event.user.id_[0]
                        bot.config.save()

                vote_callback = set_conv_admin
            voted = {}
            for u in event.conv.users:
                if not u.is_self and not UtilBot.is_user_blocked(event.conv, u.id_):
                    voted[u.full_name] = None
            bot.send_message(event.conv, "Vote started for subject: " + vote_subject)

        # Cast a vote.
        elif set_vote is not None:
            if event.user.full_name in voted.keys():
                set_vote = set_vote.lower()
                if set_vote == "true" or set_vote == "yes" or set_vote == "yea" or set_vote == "for" or set_vote == "yay" or set_vote == "aye":
                    voted[event.user.full_name] = True
                elif set_vote == "false" or set_vote == "no" or set_vote == "nay" or set_vote == "against":
                    voted[event.user.full_name] = False
                else:
                    bot.send_message(event.conv,
                                     "{}, you did not enter a valid vote parameter.".format(event.user.full_name))
                    return
            true_count = list(voted.values()).count(True)
            false_count = list(voted.values()).count(False)
            total = len(voted.values())
            if float(true_count) / float(total) > .5:
                for key in voted.keys():
                    voted[key] = True
            elif float(false_count) / float(total) > .5:
                for key in voted.keys():
                    voted[key] = False
            if not (None in voted.values()):
                yeas = 0
                nahs = 0
                for set_vote in voted.values():
                    if set_vote:
                        yeas += 1
                    else:
                        nahs += 1
                if yeas != nahs:
                    bot.send_message(event.conv,
                                     'In the matter of: "' + vote_subject + '", the ' + (
                                         'Yeas' if yeas > nahs else 'Nays') + ' have it.')
                else:
                    bot.send_message(event.conv, "The vote ended in a tie in the matter of: {}".format(vote_subject))
                if vote_callback is not None:
                    vote_callback(yeas > nahs)
                vote_subject = None
                voted = None
        # Check the status of a vote.
        else:
            if vote_subject is not None:
                segments = [hangups.ChatMessageSegment('Vote Status for "{}":'.format(vote_subject), is_bold=True),
                            hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK)]
                for person in voted.keys():
                    set_vote = voted[person]
                    segments.append(hangups.ChatMessageSegment(
                        person + " : " + ("For" if set_vote else "Not Voted" if set_vote is None else "Against")))
                    segments.append(hangups.ChatMessageSegment("\n", segment_type=hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                bot.send_message(event.conv, "No vote currently started.")