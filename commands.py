from datetime import datetime, timedelta
from fractions import Fraction
import glob
import os
import json
import random
import asyncio
import threading
import traceback
from urllib import parse
from urllib import request
import urllib

from bs4 import BeautifulSoup
from dateutil import parser
import hangups
from hangups.ui.utils import get_conv_name
import re
import requests
from setuptools.compat import execfile

import Genius
from UtilBot import UtilBot
from utils import text_to_segments


class CommandDispatcher(object):
    last_recorder = None
    last_recorded = None

    def __init__(self):
        self.commands = {}
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

    def register_unknown(self, func):
        self.unknown_command = func
        return func

# CommandDispatcher singleton
command = CommandDispatcher()
reminders = []


@command.register_unknown
def unknown_command(bot, event, *args):
    bot.send_message(event.conv,
                     '{}: Unknown command!'.format(event.user.full_name))


# Whatever new methods added here will be automatically added to the Bot's command list if they have this
# @command.register annotation. Add them in the config.json file to have them show in the /help command.
# Also, it'd be nice if all methods accepted a '?' argument to denote their function.

@command.register
def help(bot, event, *args):
    segments = [hangups.ChatMessageSegment('Current implemented commands:', is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(', '.join(sorted(command.commands.keys()))),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment('Use: /<command name> ? to find more information about the command.')]
    bot.send_message_segments(event.conv, segments)


@command.register
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


@command.register
def define(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Define', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /define <word to search for> <optional: definition number [defaults to 1st]>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Define a word.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if args[-1].isdigit():
            segments = [hangups.ChatMessageSegment(' '.join(args[0:-1]).title(), is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(
                            UtilBot.define(' '.join(args[0:-1]), num=int(args[-1])).replace('\n', ''))]
            bot.send_message_segments(event.conv, segments)
        else:
            segments = [hangups.ChatMessageSegment(' '.join(args).title(), is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(
                            UtilBot.define(' '.join(args)).replace('\n', ''))]
            bot.send_message_segments(event.conv, segments)


@command.register
def count(bot, event, *args):
    words = ' '.join(args)
    count = UtilBot.syllable_count(words)
    bot.send_message(event.conv,
                     '"' + words + '"' + " has " + str(count) + (' syllable.' if count == 1 else ' syllables.'))


@command.register
def udefine(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Urbanly Define', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /udefine <word to search for> <optional: definition number [defaults to 1st]>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Define a word.')]
        bot.send_message_segments(event.conv, segments)
    else:
        api_host = 'http://urbanscraper.herokuapp.com/search/'
        num_requested = 0
        returnall = False
        if len(args) == 0:
            return u'You need to give me a term to look up.'
        else:
            if args[-1] == '*':
                args = args[:-1]
                returnall = True
            if args[-1].isdigit():
                # we subtract one here because def #1 is the 0 item in the list
                num_requested = int(args[-1]) - 1
                args = args[:-1]

            term = urllib.parse.quote('.'.join(args))
            response = requests.get(api_host + term)
            error_response = 'No definition found for \"{}\".'.format(' '.join(args))
            if response.status_code != 200:
                bot.send_message(event.conv, error_response)
            result = response.content.decode()
            response_list = json.loads(result)
            if not response_list:
                bot.send_message(event.conv, error_response)
            result = response.content.decode()
            result_list = json.loads(result)
            num_requested = min(num_requested, len(result_list) - 1)
            num_requested = max(0, num_requested)
            result = result_list[num_requested].get(
                'definition', error_response)
            if returnall:
                segments = []
                for string in result_list:
                    segments.append(hangups.ChatMessageSegment(string))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment(' '.join(args), is_bold=True),
                            hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                            hangups.ChatMessageSegment(result + ' [{0} of {1}]'.format(
                                num_requested + 1, len(result_list)))]
                bot.send_message_segments(event.conv, segments)


@command.register
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


@command.register
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
        if (url == resp.url):
            bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Unable to find a result for \"'),
                                                   hangups.ChatMessageSegment(search_terms, is_bold=True)])
            return
        soup = BeautifulSoup(resp)

        bot.send_message_segments(event.conv, [hangups.ChatMessageSegment('Result:', is_bold=True),
                                               hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                                               hangups.ChatMessageSegment(soup.title.string, hangups.SegmentType.LINK,
                                                                          link_target=url)])


@command.register
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


@command.register
def remind(bot, event, *args):
    # TODO Implement a private chat feature. Have reminders save across reboots?
    # TODO Add a way to remove reminders.
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Remind', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind <optional: date [defaults to today]> <optional: time [defaults to an hour from now]> Message'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /remind delete <index to delete>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Will post a message the date and time specified to the current chat. With no arguments, it\'ll list all the reminders.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if len(args) == 0:
            segments = [hangups.ChatMessageSegment('Reminders:', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            if len(reminders) > 0:
                for x in range(0, len(reminders)):
                    reminder = reminders[x]
                    reminder_timer = reminder[0]
                    reminder_text = reminder[1]
                    date_to_post = datetime.now() + timedelta(seconds=reminder_timer.interval)
                    segments.append(
                        hangups.ChatMessageSegment(
                            str(x + 1) + ' - ' + date_to_post.strftime('%m/%d/%y %I:%M%p') + ' : ' + reminder_text))
                    segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.pop()
                bot.send_message_segments(event.conv, segments)
            else:
                bot.send_message(event.conv, "No reminders are currently set.")
            return
        if args[0] == 'delete':
            try:
                x = int(args[1])
                x -= 1
            except ValueError:
                bot.send_message(event.conv, 'Invalid integer: ' + args[1])
                return
            if x in range(0, len(reminders)):
                reminder_to_remove_text = reminders[x][1]
                reminders[x][0].cancel()
                reminders.remove(reminders[x])
                bot.send_message(event.conv, 'Removed reminder: ' + reminder_to_remove_text)
            else:
                bot.send_message(event.conv, 'Invalid integer: ' + str(x + 1))
            return

        def send_reminder(bot, conv, reminder_time, reminder_text, loop):
            asyncio.set_event_loop(loop)
            bot.send_message(conv, reminder_text)
            for reminder in reminders:
                if reminder[0].interval == reminder_time and reminder[1] == reminder_text:
                    reminders.remove(reminder)

        args = list(args)
        date = str(datetime.now().today().date())
        time = str((datetime.now() + timedelta(hours=1)).time())
        set_date = False
        set_time = False
        index = 0
        while index < len(args):
            item = args[index]
            if item[0].isnumeric():
                if '/' in item or '-' in item:
                    date = item
                    args.remove(date)
                    set_date = True
                    index -= 1
                else:
                    time = item
                    args.remove(time)
                    set_time = True
                    index -= 1
            if set_date and set_time:
                break
            index += 1

        reminder_time = date + ' ' + time
        if len(args) > 0:
            reminder_text = ' '.join(args)
        else:
            bot.send_message(event.conv, 'No reminder text set.')
            return
        current_time = datetime.now()
        try:
            reminder_time = parser.parse(reminder_time)
        except (ValueError, TypeError):
            bot.send_message(event.conv, "Couldn't parse " + reminder_time + " as a valid date.")
            return
        if reminder_time < current_time:
            reminder_time = current_time + timedelta(hours=1)
        reminder_interval = (reminder_time - current_time).seconds
        reminder_timer = threading.Timer(reminder_interval, send_reminder,
                                         [bot, event.conv, reminder_interval, reminder_text, asyncio.get_event_loop()])
        reminders.append((reminder_timer, reminder_text))
        reminder_timer.start()
        bot.send_message(event.conv, "Reminder set for " + reminder_time.strftime('%B %d, %Y %I:%M%p'))


@command.register
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


@command.register
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


@command.register
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


@command.register
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


@command.register
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


@command.register
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


@command.register
def finish(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Finish', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /finish <lyrics to finish> <optional: * symbol to show guessed song>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Finish a lyric!')]
        bot.send_message_segments(event.conv, segments)
    else:
        showguess = False
        if args[-1] == '*':
            showguess = True
            args = args[0:-1]
        lyric = ' '.join(args)
        songs = Genius.search_songs(lyric)

        if len(songs) < 1:
            bot.send_message(event.conv, "I couldn't find your lyrics.")
        lyrics = songs[0].raw_lyrics
        anchors = {}

        lyrics = lyrics.split('\n')
        currmin = (0, UtilBot.levenshtein_distance(lyrics[0], lyric)[0])
        for x in range(1, len(lyrics) - 1):
            try:
                currlyric = lyrics[x]
                if not currlyric.isspace():
                    # Returns the distance and whether or not the lyric had to be chopped to compare
                    result = UtilBot.levenshtein_distance(currlyric, lyric)
                else:
                    continue
                distance = abs(result[0])
                lyrics[x] = lyrics[x], result[1]

                if currmin[1] > distance:
                    currmin = (x, distance)
                if currlyric.startswith('[') and currlyric not in anchors:
                    next = UtilBot.find_next_non_blank(lyrics, x)
                    anchors[currlyric] = lyrics[next]
            except Exception:
                # TODO Sometimes this throws a 'string index out of range' error. I'm not sure why. Or where.
                # (Potentially) fixed
                # try "/finish And as I wind on down the road" to get it to occur.
                # It isn't a priority, 'cause it still find the right lyric usually.
                pass
        next = UtilBot.find_next_non_blank(lyrics, currmin[0])
        chopped = lyrics[currmin[0]][1]
        found_lyric = lyrics[currmin[0]][0] + " " + lyrics[next][0] if chopped else lyrics[next][0]
        if found_lyric.startswith('['):
            found_lyric = anchors[found_lyric]
        if showguess:
            segments = [hangups.ChatMessageSegment(found_lyric),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(songs[0].name)]
            bot.send_message_segments(event.conv, segments)
        else:
            bot.send_message(event.conv, found_lyric)

        return


@command.register
def record(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Record', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record <text to record>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record date <date to show records from>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record list'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record search <search term>'),
                    hangups.ChatMessageSegment(
                        'Usage: /record strike'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /record'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Store/Show records of conversations. Note: All records will be prepended by: \"On the day of <date>,\" automatically. ')]
        bot.send_message_segments(event.conv, segments)
    else:
        import datetime

        directory = "Records" + "\\" + str(event.conv_id)
        if not os.path.exists(directory):
            os.makedirs(directory)
        filename = str(datetime.date.today()) + ".txt"
        file = None
        if ''.join(args) == "clear":
            file = open(directory + '\\' + filename, "a+")
            file.seek(0)
            file.truncate()
        elif ''.join(args) == '':
            file = open(directory + '\\' + filename, "a+")
            # If the mode is r+, it won't create the file. If it's a+, I have to seek to the beginning.
            file.seek(0)
            segments = [hangups.ChatMessageSegment(
                'On the day of ' + datetime.date.today().strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(
                    hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        elif args[0] == "strike":
            if event.user.id_ == CommandDispatcher.last_recorder:
                file = open(directory + '\\' + filename, "a+")
                file.seek(0)
                file_lines = file.readlines()
                if CommandDispatcher.last_recorded is not None and CommandDispatcher.last_recorded in file_lines:
                    file_lines.remove(CommandDispatcher.last_recorded)
                file.seek(0)
                file.truncate()
                file.writelines(file_lines)
                CommandDispatcher.last_recorded = None
                CommandDispatcher.last_recorder = None
            else:
                bot.send_message(event.conv, "You do not have the authority to strike from the Record.")
        elif args[0] == "list":
            files = os.listdir(directory)
            segments = []
            for name in files:
                segments.append(hangups.ChatMessageSegment(name.replace(".txt", "")))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        elif args[0] == "search":
            args = args[1:]
            searched_term = ' '.join(args)
            escaped_args = []
            for item in args:
                escaped_args.append(re.escape(item))
            term = '.*'.join(escaped_args)
            term = term.replace(' ', '.*')
            if len(args) > 1:
                term = '.*' + term
            else:
                term = '.*' + term + '.*'
            foundin = []
            for name in glob.glob(directory + "\\" + '*.txt'):
                with open(name) as f:
                    contents = f.read()
                if re.match(term, contents, re.IGNORECASE | re.DOTALL):
                    foundin.append(name.replace(directory, "").replace(".txt", "").replace("\\", ""))
            if len(foundin) > 0:
                segments = [hangups.ChatMessageSegment("Found "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in:"),
                            hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK)]
                for filename in foundin:
                    segments.append(hangups.ChatMessageSegment(filename))
                    segments.append(hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                segments = [hangups.ChatMessageSegment("Couldn't find  "),
                            hangups.ChatMessageSegment(searched_term, is_bold=True),
                            hangups.ChatMessageSegment(" in any records.")]
                bot.send_message_segments(event.conv, segments)
        elif args[0] == "date":
            from dateutil import parser

            args = args[1:]
            try:
                dt = parser.parse(' '.join(args))
            except Exception as e:
                bot.send_message(event.conv, "Couldn't parse " + ' '.join(args) + " as a valid date.")
                return
            filename = str(dt.date()) + ".txt"
            try:
                file = open(directory + '\\' + filename, "r")
            except IOError:
                bot.send_message(event.conv, "No record for the day of " + dt.strftime('%B %d, %Y') + '.')
                return
            segments = [hangups.ChatMessageSegment('On the day of ' + dt.strftime('%B %d, %Y') + ':', is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
            for line in file:
                segments.append(hangups.ChatMessageSegment(line))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        else:
            file = open(directory + '\\' + filename, "a+")
            file.write(' '.join(args) + '\n')
            bot.send_message(event.conv, "Record saved successfully.")
            CommandDispatcher.last_recorder = event.user.id_
            CommandDispatcher.last_recorded = ' '.join(args) + '\n'
        if file is not None:
            file.close()


@command.register
def clear(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Clear', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /clear'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Clears the current screen.')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('Initialing', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Screen', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Removal', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Protocol', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('135:', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Just', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Going', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('To', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Remove', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('That', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('From', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('The', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Current', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('View', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('<!END PROTOCOL>', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('So how was your day?', hangups.SegmentType.LINE_BREAK)]
        bot.send_message_segments(event.conv, segments)


@command.register
def speakup(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Speakup', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /speakup'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Whistle will reply to everything.')]
        bot.send_message_segments(event.conv, segments)
    else:
        from handlers import MessageHandler

        MessageHandler.speakup(bot, event)


@command.register
def shutup(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Shut-up', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /shutup'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Whistle will only reply to its name.')]
        bot.send_message_segments(event.conv, segments)
    else:
        from handlers import MessageHandler

        MessageHandler.shutup(bot, event)


@command.register
def trash(bot, event, *args):
    bot.send_message(event.conv, "🚮")


@command.register
def restart(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Restart', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /restart'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Restarts the bot and attempts to update.')]
        bot.send_message_segments(event.conv, segments)
    else:
        import sys

        index = get_settings_index()
        if index != -1:
            sys.argv[index]["bot"] = bot
            sys.argv[index]["event"] = event
        quit(bot, event, args)
        execfile('Main.py')


def get_settings_index():
    import sys

    index = -1
    for x in range(0, len(sys.argv)):
        if isinstance(sys.argv[x], dict):
            if sys.argv[x]["isSettings"]:
                index = x
    return index


@command.register
def mute(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Mute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /mute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Mutes all non-command replies.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if bot.conv_settings[event.conv_id] is None:
            bot.conv_settings[event.conv_id] = {}
        settings = dict(bot.conv_settings[event.conv_id])
        settings['muted'] = True
        bot.conv_settings[event.conv_id] = settings


@command.register
def unmute(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Unmute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /unmute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Unmutes all non-command replies.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if bot.conv_settings[event.conv_id] is None:
            bot.conv_settings[event.conv_id] = {}
        settings = dict(bot.conv_settings[event.conv_id])
        settings['muted'] = False
        bot.conv_settings[event.conv_id] = settings


@command.register
def spoof(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Spoof', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /spoof'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Who knows...')]
        bot.send_message_segments(event.conv, segments)
    else:
        segments = [hangups.ChatMessageSegment('!!! CAUTION !!!', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('User ')]
        link = 'https://plus.google.com/u/0/{}/about'.format(event.user.id_.chat_id)
        segments.append(hangups.ChatMessageSegment(event.user.full_name, hangups.SegmentType.LINK,
                                                   link_target=link))
        segments.append(hangups.ChatMessageSegment(' has just been reporting to the NSA for attempted spoofing!'))
        bot.send_message_segments(event.conv, segments)


@command.register
def status(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Status', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /status'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Shows current status.')]
        bot.send_message_segments(event.conv, segments)
    else:

        segments = [hangups.ChatMessageSegment('Status:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Replying To All: ' + str(bot.conv_settings[event.conv_id]['clever'])),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Non-Commands: ' + 'Enabled' if not bot.conv_settings[event.conv_id]['muted'] else 'Disabled')]
        bot.send_message_segments(event.conv, segments)


@command.register
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


@command.register
def quit(bot, event, *args):
    print('HangupsBot killed by user {} from conversation {}'.format(event.user.full_name,
                                                                     get_conv_name(event.conv, truncate=True)))
    yield from bot._client.disconnect()


@command.register
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
            yield from command.unknown_command(bot, event)
            return
    else:
        yield from command.unknown_command(bot, event)
        return

    if value is None:
        value = 'Parameter does not exist!'

    config_path = ' '.join(k for k in ['config'] + config_args)
    segments = [hangups.ChatMessageSegment('{}:'.format(config_path),
                                           is_bold=True),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
    segments.extend(text_to_segments(json.dumps(value, indent=2, sort_keys=True)))
    bot.send_message_segments(event.conv, segments)


@command.register
def flip(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Flip', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /flip <optional: number of times to flip>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Flips a coin.')]
        bot.send_message_segments(event.conv, segments)
    else:
        times = 1
        if len(args) > 0 and args[-1].isdigit():
            times = int(args[-1]) if int(args[-1]) < 1000000 else 1000000
        heads, tails = 0, 0
        for x in range(0, times):
            n = random.randint(0, 1)
            if n == 1:
                heads += 1
            else:
                tails += 1
        if times == 1:
            bot.send_message(event.conv, "Heads!" if heads > tails else "Tails!")
        else:
            bot.send_message(event.conv,
                             "Winner: " + (
                                 "Heads!" if heads > tails else "Tails!" if tails > heads else "Tie!") + " Heads: " + str(
                                 heads) + " Tails: " + str(tails) + " Ratio: " + (str(
                                 Fraction(heads, tails)) if heads > 0 and tails > 0 else str(heads) + '/' + str(tails)))


@command.register
def add(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Add', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /add word <word to add>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Adds a word to the Unhashtagger.')]
        bot.send_message_segments(event.conv, segments)
    else:
        if args[0] == "word":
            args = args[1:]
            from UtilBot import UtilBot

            UtilBot.add_word(''.join(args))


@command.register
def quote(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Quote', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /quote <optional: terms to search for> <optional: number of quote to show>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Shows a quote.')]
        bot.send_message_segments(event.conv, segments)
    else:
        USER_ID = "3696"
        DEV_ID = "ZWBWJjlb5ImJiwqV"
        QUERY_TYPE = "RANDOM"
        fetch = 0
        if len(args) > 0 and args[-1].isdigit():
            fetch = int(args[-1])
            args = args[:-1]
        query = '+'.join(args)
        if len(query) > 0:
            QUERY_TYPE = "SEARCH"
        url = "http://www.stands4.com/services/v2/quotes.php?uid=" + USER_ID + "&tokenid=" + DEV_ID + "&searchtype=" + QUERY_TYPE + "&query=" + query
        soup = BeautifulSoup(request.urlopen(url))
        if QUERY_TYPE == "SEARCH":
            children = list(soup.results.children)
            numQuotes = len(children)
            if numQuotes == 0:
                bot.send_message(event.conv, "Unable to find quote.")
                return

            if fetch > numQuotes - 1:
                fetch = numQuotes
            elif fetch < 1:
                fetch = 1
            bot.send_message(event.conv, "\"" +
                             children[fetch - 1].quote.text + "\"" + ' - ' + children[
                fetch - 1].author.text + ' [' + str(
                fetch) + ' of ' + str(numQuotes) + ']')
        else:
            bot.send_message(event.conv, "\"" + soup.quote.text + "\"" + ' -' + soup.author.text)


@command.register
def block(bot, event, username, *args):
    username_lower = username.strip().lower()
    for u in sorted(bot._user_list._user_dict.values(), key=lambda x: x.full_name.split()[-1]):
        if not username_lower in u.full_name.lower():
            continue
        from handlers import MessageHandler

        MessageHandler.blocked_list.append(u.id_)
        bot.send_message(event.conv, "Blocked User: {}".format(u.full_name))