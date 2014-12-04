from fractions import Fraction
import glob
import os
import string
import json
import random
import asyncio
from urllib import parse
from urllib import request
import urllib
import re

import goslate
import hangups
from hangups.ui.utils import get_conv_name
import requests
from wikia import wikia, WikiaError

import Genius
from UtilBot import UtilBot
from utils import text_to_segments


class CommandDispatcher(object):
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
            print(e)

    def register(self, func):
        """Decorator for registering command"""
        self.commands[func.__name__] = func
        return func

    def register_unknown(self, func):
        self.unknown_command = func
        return func

# CommandDispatcher singleton
command = CommandDispatcher()


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
                            UtilBot.search(' '.join(args[0:-1]), num=int(args[-1])).replace('\n', ''))]
            bot.send_message_segments(event.conv, segments)
        else:
            segments = [hangups.ChatMessageSegment(' '.join(args).title(), is_bold=True),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(
                            UtilBot.search(' '.join(args)).replace('\n', ''))]
            bot.send_message_segments(event.conv, segments)


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
def test(bot, event, *args):
    segments = [
        hangups.ChatMessageSegment("title", is_bold=True, hangups.SegmentType.LINK, link_target="www.google.com"),
        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)`]

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
                page = wikipedia.page(wikipedia.search(' '.join(args), results=1)[0])
            segments = [
                hangups.ChatMessageSegment(page.title, hangups.SegmentType.LINK, is_bold=True, link_target=page.url),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(page.summary(sentences=sentences))]

            bot.send_message_segments(event.conv, segments)
        except PageError:
            bot.send_message(event.conv, "Couldn't find \"{}\". Try something else.".format(' '.join(args)))


@command.register
def goog(bot, event, *args):
    def get_json_results(page):
        search_results = page.read()
        results = json.loads(search_results.decode('utf-8'))
        segments = [hangups.ChatMessageSegment('{}:'.format("Result"), is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment("".join(str(results['responseData']['results'][0]['titleNoFormatting'])),
                                               hangups.SegmentType.LINK,
                                               link_target="".join(str(results['responseData']['results'][0]['url'])))]
        bot.send_message_segments(event.conv, segments)

    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Google', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /goog <optional: search parameter>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Get the first result from Google\'s search using search parameter.')]
        bot.send_message_segments(event.conv, segments)
    else:
        rest = " ".join(args)
        if rest == "" or rest == " ":
            rest = "google"
        query = parse.urlencode({'q': rest})
        url = 'http://ajax.googleapis.com/ajax/services/search/web?v=1.0&%s' \
              % query
        headers = {
            'User-agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36'}
        req = request.Request(url, None, headers)
        search_response_d = request.urlopen(req)

        get_json_results(search_response_d)
        return search_response_d


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
                        'Purpose: Lies to you.')]
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
def destiny(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Destiny', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /destiny <keyword to search for> <optional: characters to display [default = 500]>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Get information about a Destiny topic.')]
        bot.send_message_segments(event.conv, segments)
    else:
        try:
            characters = 500

            if args[-1].isdigit():
                characters = args[-1]
                page = wikia.page('Destiny', wikia.search(' '.join(args[0:-1]), 'destiny')[0])
            else:
                page = wikia.page('Destiny', wikia.search(' '.join(args), 'destiny')[0])
            segments = [
                hangups.ChatMessageSegment(page.title.title(), hangups.SegmentType.LINK, is_bold=True,
                                           link_target=page.url),
                hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                hangups.ChatMessageSegment(wikia.summary(page.original_title, 'Destiny', chars=characters))]

            bot.send_message_segments(event.conv, segments)
        except WikiaError:
            bot.send_message(event.conv, "Couldn't find '{}'. Try something else.".format(' '.join(args)))


@command.register
def guessthesong(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Guess The Song', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /guessthesong <lyric in song>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Guessing a song!')]
        bot.send_message_segments(event.conv, segments)
    else:
        regex = re.compile('[%s]' % re.escape(string.punctuation))
        results = 1
        if args[-1].isdigit():
            results = int(args[-1])

        lyric = regex.sub('', ' '.join(args))
        songs = Genius.search_songs(lyric)
        results = len(songs) if results > len(songs) else results
        segments = []

        for x in range(0, results):
            segments.append(hangups.ChatMessageSegment(songs[x].name))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        if len(segments) == 0:
            bot.send_message(event.conv, "I couldn't guess the song...")
        else:
            bot.send_message_segments(event.conv, segments)


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
                if currlyric.startswith('['):
                    next = UtilBot.find_next_non_blank(lyrics, x)
                    anchors[currlyric] = lyrics[next][0]
                if lyric in anchors:
                    bot.send_message(event.conv, str(anchors[lyric]))
                    return
            except Exception:
                # TODO Sometimes this throws a 'string index out of range' error. I'm not sure why. Or where.
                # try "/finish And as I wind on down the road" to get it to occur.
                # It isn't a priority, 'cause it still find the right lyric usually.
                pass
        next = UtilBot.find_next_non_blank(lyrics, currmin[0])
        chopped = lyrics[currmin[0]][1]
        foundlyric = lyrics[currmin[0]][0] + " " + lyrics[next][0] if chopped else lyrics[next][0]
        if showguess:
            segments = [hangups.ChatMessageSegment(foundlyric),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                        hangups.ChatMessageSegment(songs[0].name)]
            bot.send_message_segments(event.conv, segments)
        else:
            bot.send_message(event.conv, foundlyric)

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
        elif args[0] == "list":
            files = os.listdir(directory)
            segments = []
            for name in files:
                segments.append(hangups.ChatMessageSegment(name.replace(".txt", "")))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            bot.send_message_segments(event.conv, segments)
        elif args[0] == "search":
            args = args[1:]
            term = ' '.join(args)
            foundin = []
            for name in glob.glob(directory + "\\" + '*.txt'):
                with open(name) as f:
                    contents = f.read()
                if term.lower() in contents.lower():
                    foundin.append(name.replace(directory, "").replace(".txt", "").replace("\\", ""))
            if len(foundin) > 0:
                segments = [hangups.ChatMessageSegment("Found "),
                            hangups.ChatMessageSegment(term, is_bold=True),
                            hangups.ChatMessageSegment(" in:"),
                            hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK)]
                for file in foundin:
                    segments.append(hangups.ChatMessageSegment(file))
                    segments.append(hangups.ChatMessageSegment("\n", hangups.SegmentType.LINE_BREAK))
                bot.send_message_segments(event.conv, segments)
            else:
                bot.send_message(event.conv, "Couldn't find \"" + term + "\" in any records.")
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
        if file is not None:
            file.close()


@command.register
def obscure(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Obscure', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Usage: /obscure <text to obscure> <optional: number of times to obscure>'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Purpose: Runs your text through Google Translate a lot. Defaults to 14 times.)')]
        bot.send_message_segments(event.conv, segments)
    else:
        translator = goslate.Goslate()
        languages = ['en', 'de', 'af', 'zh-CN', 'xx-elmer', 'fi', 'fr', 'xx-pirate', 'ro',
                     'es', 'sk', 'tr', 'vi', 'cy']
        showall = False
        if args[-1] == '*':
            showall = True
            args = args[0:-1]
        times = len(languages)
        if args[-1].isdigit():
            times = int(args[-1])
            args = args[0:-1]
        text = ' '.join(args)
        translations = [hangups.ChatMessageSegment(text),
                        hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
        for x in range(0, times):
            text = translator.translate(text, languages[random.randint(0, len(languages) - 1)])
            if showall:
                translations.append(hangups.ChatMessageSegment(text))
                translations.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        text = translator.translate(text, 'en')
        if showall:
            translations.append(hangups.ChatMessageSegment(text))
            bot.send_message_segments(event.conv, translations)
        else:
            bot.send_message(event.conv, text)


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


# @command.register
# def easteregg(bot, event, easteregg, eggcount=1, period=0.5, *args):
#
# for i in range(int(eggcount)):
# yield from bot._client.sendeasteregg(event.conv_id, easteregg)
# if int(eggcount) > 1:
# yield from asyncio.sleep(float(period) + random.uniform(-0.1, 0.1))


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
                    hangups.ChatMessageSegment('Purpose: Whistle will only reply to his name.')]
        bot.send_message_segments(event.conv, segments)
    else:
        from handlers import MessageHandler

        MessageHandler.shutup(bot, event)


@command.register
def trash(bot, event, *args):
    bot.send_message(event.conv, "🚮")


@command.register
def restart(bot, event, *args):
    import os

    os.system('python Main.py')
    quit(bot, event, args)


@command.register
def mute(bot, event, *args):
    if ''.join(args) == '?':
        segments = [hangups.ChatMessageSegment('Mute', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Usage: /mute'),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Purpose: Mutes the Cleverbot replies')]
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
                    hangups.ChatMessageSegment('Purpose: Unmutes the Cleverbot replies')]
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
        import handlers

        segments = [hangups.ChatMessageSegment('Status:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment('Replying To All: ' + str(bot.conv_settings[event.conv_id]['clever'])),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK),
                    hangups.ChatMessageSegment(
                        'Replying To Name: ' + str(not bot.conv_settings[event.conv_id]['muted']))]
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
    bot.send_message(event.conv, "Creator, why hast thou forsaken me?!")
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
    bot.send_message(event.conv,
                     "Winner: " + (
                         "Heads!" if heads > tails else "Tails!" if tails > heads else "Tie!") + " Heads: " + str(
                         heads) + " Tails: " + str(tails) + " Ratio: " + (str(
                         Fraction(heads, tails)) if heads > 0 and tails > 0 else str(heads) + '/' + str(tails)))


@command.register
def fortune(bot, event, *args):
    """Give a random fortune"""
    url = "http://www.fortunecookiemessage.com"
    html = request.urlopen(url).read().decode('utf-8')
    m = re.search("class=\"cookie-link\">(<p>)?", html)
    m = re.search("(</p>)?</a>", html[m.end():])
    bot.send_message(event.conv, m.string[:m.start()])


@command.register
def acrostic(bot, event, *args):
    words = open('wordlist.txt').read().strip().split()
    for arg in args:
        letters = [letter.lower() for letter in arg]
        random_words = []
        for index, letter in enumerate(letters):
            if index == len(arg) - 1:
                random_words.append(
                    random.choice([word for word in words if word[0].lower() == letter and word[len(word) - 2] != "'"]))
            else:
                random_words.append(random.choice([word for word in words if word[0].lower() == letter]))

        random_words = " ".join([word[0].upper() + word[1:] for word in random_words])

        msg = "".join([letter.upper() for letter in letters]) + ": " + random_words
        bot.send_message(event.conv, msg)

# TODO Add a name function.
