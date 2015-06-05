import asyncio
from datetime import timedelta, datetime
from fractions import Fraction
import glob
import json
import os
import random
import threading
from urllib import parse, request
from bs4 import BeautifulSoup
from dateutil import parser
import dateutil
import hangups
import re
import requests
import parsedatetime
from Core.Commands.Dispatcher import DispatcherSingleton
from Core.Util import UtilBot
from Libraries import Genius

currently_running_reminders = []


@DispatcherSingleton.register
def count(bot, event, *args):
    words = ' '.join(args)
    count = UtilBot.syllable_count(words)
    bot.send_message(event.conv,
                     '"' + words + '"' + " has " + str(count) + (' syllable.' if count == 1 else ' syllables.'))


@DispatcherSingleton.register
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
            bot.send_message(event.conv, "Invalid usage of /udefine.")
            return
        else:
            if args[-1] == '*':
                args = args[:-1]
                returnall = True
            if args[-1].isdigit():
                # we subtract one here because def #1 is the 0 item in the list
                num_requested = int(args[-1]) - 1
                args = args[:-1]

            term = parse.quote('.'.join(args))
            response = requests.get(api_host + term)
            error_response = 'No definition found for \"{}\".'.format(' '.join(args))
            if response.status_code != 200:
                bot.send_message(event.conv, error_response)
            result = response.content.decode()
            result_list = json.loads(result)
            if len(result_list) == 0:
                bot.send_message(event.conv, error_response)
                return
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


# Function for sending reminders to a chat.
def send_reminder(bot, conv, reminder_time, reminder_text, loop):
    asyncio.set_event_loop(loop)
    bot.send_message(conv, "Reminder: " + reminder_text)
    UtilBot.delete_reminder(conv.id_, reminder_text, reminder_time)


def _reminder_on_connect_listener(bot):
    reminders = UtilBot.get_all_reminders()
    for reminder in reminders:
        reminder_time = dateutil.parser.parse(reminder[2])
        reminder_interval = (reminder_time - datetime.now()).seconds
        conv = bot._conv_list.get(reminder[0])
        reminder_timer = threading.Timer(reminder_interval, send_reminder,
                                         [bot, conv, reminder_interval, reminder[1], asyncio.get_event_loop()])
        reminder_timer.start()


@DispatcherSingleton.register_extras(on_connect_listener=_reminder_on_connect_listener)
def remind(bot, event, *args):
    # TODO Implement a private chat feature. Have reminders save across reboots?
    """
    **Remind:**
    Usage: /remind <optional: date [defaults to today]> <optional: time [defaults to an hour from now]> <message> {/remind 1/1/15 2:00PM Call mom}
    Usage: /remind
    Usage /remind delete <index to delete> {/remind delete 1}
    Purpose: Will post a message on the date and time specified to the current chat. With no arguments, it'll list all the reminders."""

    # Show all reminders
    if len(args) == 0:
        segments = [hangups.ChatMessageSegment('Reminders:', is_bold=True),
                    hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK)]
        reminders = UtilBot.get_all_reminders(event.conv_id)
        if len(reminders) > 0:
            for x in range(0, len(reminders)):
                reminder = reminders[x]
                reminder_text = reminder[1]
                date_to_post = dateutil.parser.parse(reminder[2])
                segments.append(
                    hangups.ChatMessageSegment(
                        str(x + 1) + ' - ' + date_to_post.strftime('%m/%d/%y %I:%M%p') + ' : ' + reminder_text))
                segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
            segments.pop()
            bot.send_message_segments(event.conv, segments)
        if len(segments) <= 2:
            bot.send_message(event.conv, "No reminders set for this chat.")
        return

    # Delete a reminder
    if args[0] == 'delete':
        try:
            x = int(args[1])
            x -= 1
        except ValueError:
            bot.send_message(event.conv, 'Invalid integer: ' + args[1])
            return
        reminders = UtilBot.get_all_reminders(event.conv_id)
        reminder_to_delete_text = None
        if x in range(0, len(reminders)):
            to_delete_reminder = reminders[x]
            for running_reminder in currently_running_reminders:
                if running_reminder[1] == to_delete_reminder:
                    running_reminder[0].cancel()
        if reminder_to_delete_text:
            bot.send_message(event.conv, 'Removed reminder: ' + str(reminder_to_delete_text))
        else:
            bot.send_message(event.conv, 'The reminder chosen is not currently running.')
        return

    # Set a new reminder
    args = list(args)
    reminder_text = ' '.join(args)
    c = parsedatetime.Calendar()
    result = c.nlp(reminder_text)
    if result is None:
        bot.send_message(event.conv, "Couldn't parse a valid date from {}'s message.".format(event.user.full_name))
        return
    reminder_time = result[0][0]
    reminder_text = reminder_text.replace(result[0][-1], '')
    if reminder_text.strip() == '':
        bot.send_message(event.conv, 'No reminder text set.')
        return

    current_time = datetime.now()
    if reminder_time < current_time:
        bot.send_message("Invalid Date: {}".format(reminder_time.strftime('%B %d, %Y %I:%M%p')))

    reminder_interval = (reminder_time - current_time).total_seconds()

    reminder_timer = threading.Timer(reminder_interval, send_reminder,
                                     [bot, event.conv, reminder_interval, reminder_text, asyncio.get_event_loop()])
    UtilBot.add_reminder(event.conv_id, reminder_text, reminder_time)
    reminder_timer.start()
    currently_running_reminders.append((reminder_timer, (event.conv_id, reminder_text, reminder_time)))
    bot.send_message(event.conv, "Reminder set for " + reminder_time.strftime('%B %d, %Y %I:%M%p'))


@DispatcherSingleton.register
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


@DispatcherSingleton.register
def record(bot, event, *args):
    """
    **Record:**
    Usage: /record <text to record>
    Usage: /record date <date to show records from>
    Usage: /record list
    Usage: /record search <search term>
    Usage: /record strike
    Usage: /record
    Purpose: Store/Show records of conversations. Note: All records will be prepended by: "On the day of <date>," automatically.
    """

    import datetime

    directory = "Records" + os.sep + str(event.conv_id)
    if not os.path.exists(directory):
        os.makedirs(directory)
    filename = str(datetime.date.today()) + ".txt"
    filepath = os.path.join(directory, filename)
    file = None

    # Deletes the record for the day.
    if ''.join(args) == "clear":
        file = open(filepath, "a+")
        file.seek(0)
        file.truncate()

    # Shows the record for the day.
    elif ''.join(args) == '':
        file = open(filepath, "a+")
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

    # Removes the last line recorded, iff the user striking is the same as the person who recorded last.
    elif args[0] == "strike":
        last_recorder = UtilBot.get_last_recorder(event.conv_id)
        last_recorded = UtilBot.get_last_recorded(event.conv_id)
        if event.user.id_ == last_recorder:
            file = open(filepath, "a+")
            file.seek(0)
            file_lines = file.readlines()
            if last_recorded is not None and last_recorded in file_lines:
                file_lines.remove(last_recorded)
            file.seek(0)
            file.truncate()
            file.writelines(file_lines)
            UtilBot.set_last_recorded(event.conv_id, None)
            UtilBot.set_last_recorder(event.conv_id, None)
        else:
            bot.send_message(event.conv, "You do not have the authority to strike from the Record.")

    # Lists every record available. TODO Paginate this?
    elif args[0] == "list":
        files = os.listdir(directory)
        segments = []
        for name in files:
            segments.append(hangups.ChatMessageSegment(name.replace(".txt", "")))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
        bot.send_message_segments(event.conv, segments)

    # Shows a list of records that match the search criteria.
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
        for name in glob.glob(directory + os.sep + '*.txt'):
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

    # Lists a record from the specified date.
    elif args[0] == "date":
        from dateutil import parser

        args = args[1:]
        try:
            dt = parser.parse(' '.join(args))
        except Exception as e:
            bot.send_message(event.conv, "Couldn't parse " + ' '.join(args) + " as a valid date.")
            return
        filename = str(dt.date()) + ".txt"
        filepath = os.path.join(directory, filename)
        try:
            file = open(filepath, "r")
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

    # Saves a record.
    else:
        file = open(filepath, "a+")
        file.write(' '.join(args) + '\n')
        bot.send_message(event.conv, "Record saved successfully.")
        UtilBot.set_last_recorder(event.conv_id, event.user.id_)
        UtilBot.set_last_recorded(event.conv_id, ' '.join(args) + '\n')
    if file is not None:
        file.close()


@DispatcherSingleton.register
def trash(bot, event, *args):
    bot.send_message(event.conv, "🚮")


@DispatcherSingleton.register
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


@DispatcherSingleton.register
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


@DispatcherSingleton.register
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
