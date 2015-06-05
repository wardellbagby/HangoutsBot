from bisect import bisect_left
from datetime import datetime, timedelta
import os
from urllib import request
from bs4 import BeautifulSoup, Tag
import re
import hangups
import sqlite3
from Core.Util import UtilDB

__author__ = 'wardellchandler'

# TODO I think this is a relic of Bots Past. Check into whether it's needed.
words = open("Core" + os.sep + "Util" + os.sep + "wordlist.txt")
word_list = []
for line in words:
    word_list.append(line.strip('\n'))
word_list.sort()

# Blocklist
_blocklist = {}

# For the /vote command.
_vote_subject = {}
_voted_tally = {}
_vote_callbacks = {}

# For the /record command
_last_recorder = {}
_last_recorded = {}

_url_regex = r"^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$"



def is_user_conv_admin(bot, user_info, conv_id=None):
    if isinstance(user_info, hangups.ConversationEvent):
        user_id = user_info.user_id
        conv_id = user_info.conversation_id
    elif isinstance(user_info, str):
        user_id = user_info
    elif isinstance(user_info, hangups.user.User):
        user_id = user_info.user_id[0]
    elif isinstance(user_info, hangups.user.UserID):
        user_id = user_info[0]

    if conv_id is None:
        raise ValueError("conv_id can not be None.")

    if user_id is None:
        raise ValueError("user_info can not be null")

    conv_admin_list = bot.get_config_suboption(conv_id, 'conversation_admin')
    return conv_admin_list and user_id in conv_admin_list


def is_user_admin(bot, user_info, conv_id=None):
    user_id = None
    if isinstance(user_info, hangups.ConversationEvent):
        user_id = user_info.user_id
        conv_id = user_info.conversation_id
    elif isinstance(user_info, str):
        user_id = user_info
    elif isinstance(user_info, hangups.user.User):
        user_id = user_info.user_id[0]
    elif isinstance(user_info, hangups.user.UserID):
        user_id = user_info[0]

    if conv_id is None:
        raise ValueError("conv_id can not be None.")

    if user_id is None:
        raise ValueError("user_info does not contain valid User information.")

    admins_list = bot.get_config_suboption(conv_id, 'admins')
    return admins_list and user_id in admins_list


def check_if_can_run_command(bot, event, command):
    commands_admin_list = bot.get_config_suboption(event.conv_id, 'commands_admin')
    commands_conv_admin_list = bot.get_config_suboption(event.conv_id, 'commands_conversation_admin')
    admins_list = bot.get_config_suboption(event.conv_id, 'admins')
    conv_admin = bot.get_config_suboption(event.conv_id, 'conversation_admin')


    # Check if this is a conversation admin command.
    if commands_conv_admin_list and (command in commands_conv_admin_list):
        if (admins_list and event.user_id[0] not in admins_list) \
                and (conv_admin and event.user_id[0] != conv_admin):
            return False

    # Check if this is a admin-only command.
    if commands_admin_list and (command in commands_admin_list):
        if not admins_list or event.user_id[0] not in admins_list:
            return False
    return True


def get_vote_subject(conv_id):
    if conv_id in _vote_subject:
        return _vote_subject[conv_id]
    return None


# userlist is a array of User objects, not an array of names.
def init_new_vote(conv_id, userlist):
    _voted_tally[conv_id] = {}
    _vote_callbacks[conv_id] = None
    for user in userlist:
        if not user.is_self:
            _voted_tally[conv_id][user.full_name] = None


def set_vote_subject(conv_id, subject):
    _vote_subject[conv_id] = subject.strip()


def set_vote(conv_id, username, vote):
    if conv_id not in _voted_tally:
        _voted_tally[conv_id] = {}
    _voted_tally[conv_id][username] = vote


def abstain_voter(conv_id, username):
    if username in _voted_tally[conv_id]:
        del _voted_tally[conv_id][username]
    if len(_voted_tally[conv_id]) == 0:
        end_vote(conv_id)
        return True


def get_vote_status(conv_id):
    results = ["**Vote Status for {}:**".format(get_vote_subject(conv_id))]
    for person in _voted_tally[conv_id]:
        results.append(person + ' : ' + str(get_vote(conv_id, person)))

    return results


def get_vote(conv_id, username):
    if is_vote_started(conv_id):
        try:
            return _voted_tally[conv_id][username]
        except KeyError:
            return None


def check_if_vote_finished(conv_id):
    voted = _voted_tally[conv_id]
    true_count = list(voted.values()).count(True)
    false_count = list(voted.values()).count(False)
    total = len(voted.values())
    if total == 0:
        return None
    if float(true_count) / float(total) > .5:
        for key in voted.keys():
            voted[key] = True
    elif float(false_count) / float(total) > .5:
        for key in voted.keys():
            voted[key] = False
    if not (None in voted.values()):
        yeas = 0
        nahs = 0
        for tallied_vote in voted.values():
            if tallied_vote:
                yeas += 1
            else:
                nahs += 1
        return yeas - nahs
    else:
        return None


def set_vote_callback(conv_id, callback):
    _vote_callbacks[conv_id] = callback


def can_user_vote(conv_id, user):
    try:
        is_voting = user.full_name in _voted_tally[conv_id]
        try:
            is_blocked = user.id_ in _blocklist[conv_id]
        except KeyError:
            is_blocked = False  # For the case that the blocklist hasn't been init'd.

        return is_voting and not is_blocked
    except KeyError:
        return False


def is_vote_started(conv_id):
    try:
        return _vote_subject[conv_id] is not None and _voted_tally[conv_id] is not None
    except KeyError:
        return False


def end_vote(conv_id, vote_result=False):
    if vote_result and _vote_callbacks[conv_id] is not None:
        _vote_callbacks[conv_id]()
    del _voted_tally[conv_id]
    _vote_subject[conv_id] = None
    del _vote_callbacks[conv_id]


def find_private_conversation(conv_list, user_id, default=None):
    for conv_id in conv_list._conv_dict.keys():
        current_conv = conv_list.get(conv_id)
        if len(current_conv.users) == 2:

            # Just in case the bot has a reference to a conversation it isn't actually in anymore.
            if not (current_conv.users[0].is_self or current_conv.users[1].is_self):
                continue

            # Is the user in this conversation?
            if user_id in [user.id_ for user in current_conv.users]:
                return current_conv
    return default


def add_to_blocklist(conv_id, user_id):
    if conv_id not in _blocklist.keys():
        _blocklist[conv_id] = []
    _blocklist[conv_id].append(user_id)


def is_user_blocked(conv_id, user_id):
    if conv_id in _blocklist.keys():
        return user_id in _blocklist[conv_id]
    return False


def get_blocked_users_in_conversations(conv_id):
    if conv_id in _blocklist.keys():
        return _blocklist[conv_id]
    return []


def remove_from_blocklist(conv_id, user_id):
    if is_user_blocked(conv_id, user_id):
        _blocklist[conv_id].remove(user_id)


def check(string):
    return string.replace("&#39", "'")


def define(word, num=1):
    if num < 1:
        num = 1
    try:
        url = "http://wordnetweb.princeton.edu/perl/webwn?s=" + word + "&sub=Search+WordNet&o2=&o0=&o8=1&o1=1&o7=&o5=&o9=&o6=&o3=&o4=&h=0000000000"
    except Exception as e:
        print(e)
        return 'Couldn\'t download definition.'
    try:
        soup = BeautifulSoup(request.urlopen(url))
    except:
        return "Network Error: Couldn't download definition.", 0
    if soup.ul is not None:
        definitions = [x.text for x in list(soup.ul) if isinstance(x, Tag) and x.text != '\n' and x.text != '']
        if len(definitions) >= num:
            return (definitions[num - 1] + '[' + str(num) + ' of ' + str(len(definitions)) + ']')[
                   3:].capitalize(), len(definitions)
    return "Couldn\'t find definition.", 0


def levenshtein_distance(first, second):
    """Find the Levenshtein distance between two strings."""
    chopped = False
    if len(first) > len(second):
        first = first[:len(second)]
        first, second = second, first
        chopped = True
    if len(second) == 0:
        return len(first)
    first_length = len(first) + 1
    second_length = len(second) + 1
    distance_matrix = [[0] * second_length for x in range(first_length)]
    for i in range(first_length):
        distance_matrix[i][0] = i
    for j in range(second_length):
        distance_matrix[0][j] = j
    for i in range(1, first_length):
        for j in range(1, second_length):
            deletion = distance_matrix[i - 1][j] + 1
            insertion = distance_matrix[i][j - 1] + 1
            substitution = distance_matrix[i - 1][j - 1]
            if first[i - 1] != second[j - 1]:
                substitution += 1
            distance_matrix[i][j] = min(insertion, deletion, substitution)
    return distance_matrix[first_length - 1][second_length - 1], chopped


def find_next_non_blank(list, start=0):
    for x in range(start + 1, len(list)):
        if isinstance(list[x], tuple):
            tocheck = list[x][0]
        else:
            tocheck = list[x]
        tocheck = tocheck.replace(' ', '')
        if tocheck != '':
            return x


def syllable_count(word):
    word = word.lower()

    # exception_add are words that need extra syllables
    # exception_del are words that need less syllables

    exception_add = ['serious', 'crucial']
    exception_del = ['fortunately', 'unfortunately']

    co_one = ['cool', 'coach', 'coat', 'coal', 'count', 'coin', 'coarse', 'coup', 'coif', 'cook', 'coign', 'coiffe',
              'coof', 'court']
    co_two = ['coapt', 'coed', 'coinci']

    pre_one = ['preach']

    syls = 0  # added syllable number
    disc = 0  # discarded syllable number

    # 1) if letters < 3 : return 1
    if len(word) <= 3:
        syls = 1
        return syls

    # 2) if doesn't end with "ted" or "tes" or "ses" or "ied" or "ies", discard "es" and "ed" at the end.
    # if it has only 1 vowel or 1 set of consecutive vowels, discard. (like "speed", "fled" etc.)

    if word[-2:] == "es" or word[-2:] == "ed":
        doubleAndtripple_1 = len(re.findall(r'[eaoui][eaoui]', word))
        if doubleAndtripple_1 > 1 or len(re.findall(r'[eaoui][^eaoui]', word)) > 1:
            if word[-3:] == "ted" or word[-3:] == "tes" or word[-3:] == "ses" or word[-3:] == "ied" or word[
                                                                                                       -3:] == "ies":
                pass
            else:
                disc += 1

    # 3) discard trailing "e", except where ending is "le"

    le_except = ['whole', 'mobile', 'pole', 'male', 'female', 'hale', 'pale', 'tale', 'sale', 'aisle', 'whale',
                 'while']

    if word[-1:] == "e":
        if word[-2:] == "le" and word not in le_except:
            pass

        else:
            disc += 1

    # 4) check if consecutive vowels exists, triplets or pairs, count them as one.

    doubleAndtripple = len(re.findall(r'[eaoui][eaoui]', word))
    tripple = len(re.findall(r'[eaoui][eaoui][eaoui]', word))
    disc += doubleAndtripple + tripple

    # 5) count remaining vowels in word.
    numVowels = len(re.findall(r'[eaoui]', word))

    # 6) add one if starts with "mc"
    if word[:2] == "mc":
        syls += 1

    # 7) add one if ends with "y" but is not surrouned by vowel
    if word[-1:] == "y" and word[-2] not in "aeoui":
        syls += 1

    # 8) add one if "y" is surrounded by non-vowels and is not in the last word.

    for i, j in enumerate(word):
        if j == "y":
            if (i != 0) and (i != len(word) - 1):
                if word[i - 1] not in "aeoui" and word[i + 1] not in "aeoui":
                    syls += 1

    # 9) if starts with "tri-" or "bi-" and is followed by a vowel, add one.

    if word[:3] == "tri" and word[3] in "aeoui":
        syls += 1

    if word[:2] == "bi" and word[2] in "aeoui":
        syls += 1

    # 10) if ends with "-ian", should be counted as two syllables, except for "-tian" and "-cian"

    if word[-3:] == "ian":
        # and (word[-4:] != "cian" or word[-4:] != "tian") :
        if word[-4:] == "cian" or word[-4:] == "tian":
            pass
        else:
            syls += 1

    # 11) if starts with "co-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.

    if word[:2] == "co" and word[2] in 'eaoui':

        if word[:4] in co_two or word[:5] in co_two or word[:6] in co_two:
            syls += 1
        elif word[:4] in co_one or word[:5] in co_one or word[:6] in co_one:
            pass
        else:
            syls += 1

    # 12) if starts with "pre-" and is followed by a vowel, check if exists in the double syllable dictionary, if not, check if in single dictionary and act accordingly.

    if word[:3] == "pre" and word[3] in 'eaoui':
        if word[:6] in pre_one:
            pass
        else:
            syls += 1

    # 13) check for "-n't" and cross match with dictionary to add syllable.

    negative = ["doesn't", "isn't", "shouldn't", "couldn't", "wouldn't"]

    if word[-3:] == "n't":
        if word in negative:
            syls += 1
        else:
            pass

            # 14) Handling the exceptional words.

    if word in exception_del:
        disc += 1

    if word in exception_add:
        syls += 1

        # calculate the output
    return numVowels - disc + syls


def is_haiku(message):
    message = message.lower().replace('\xa0', " ")
    import string

    for c in string.punctuation:
        message = message.replace(c, "")
    words = re.split('\s+', message)
    total = 0
    for word in words:
        total += syllable_count(word)
    return True if total == 17 else False


def convert_to_haiku(message):
    message = message.replace('\xa0', " ")
    words_with_puncs = [x for x in re.split('\s+', message) if x != '' and x is not None]
    import string

    for c in string.punctuation:
        message = message.replace(c, "")
    words = [x for x in message.split(' ') if x != '' and x is not None]
    total = 0
    start = 0
    index = 0
    haiku = ''
    lines = 0
    current_measure = 5
    while index < len(words) and lines < 3:
        total += syllable_count(words[index])
        if total > current_measure:
            return None
        if total == current_measure:
            current_measure = 7 if current_measure == 5 else 5
            haiku += ' '.join(words_with_puncs[start:index + 1]) + '\n'
            total = 0
            lines += 1
            start = index + 1
        index += 1
    return haiku


def binary_search(a, x, lo=0, hi=None):
    hi = hi if hi is not None else len(a)
    pos = bisect_left(a, x, lo, hi)
    return pos if pos != hi and a[pos] == x else ~pos


def add_word(word):
    pos = binary_search(word_list, word)
    if pos > -1:
        return
    word_list.insert(~pos, word)
    global words
    words = open('wordlist.txt', 'w+')
    words.seek(0)
    for word in word_list:
        words.write(word + '\n')
    words.close()


def unhashtag(self, message):
    hashtagged = str(message)
    pattern = re.compile(r'(#[a-zA-Z]+\'*[a-zA-Z]*)')
    matches = pattern.findall(hashtagged)
    to_return = []
    for match in matches:
        match = match[1:]
        x = len(match)
        while x > 0:
            if self.binary_search(self.list, match[0:x].lower()) > -1:
                to_return.append(match[0:x] + ' ')
                match = match[x:]
                x = len(match)
            else:
                x -= 1
        if len(match) > 0:
            to_return.append('[' + match + ']')
        to_return.append('\n')
    return to_return if to_return != [] else None


# Uses basic markdown syntax for italics and bold.
def text_to_segments(text):
    if not text:
        return []

    # Replace two consecutive spaces with space and non-breakable space, strip of leading/trailing spaces,
    # then split text to lines
    lines = [x.strip() for x in text.replace('  ', ' \xa0').splitlines()]

    # Generate line segments
    segments = []
    for line in lines[:-1]:
        if line:
            if line[:2] == '**' and line[-2:] == '**':
                line = line[2:-2]
                segments.append(hangups.ChatMessageSegment(line, is_bold=True))
            elif line[0] == '*' and line[-1] == '*':
                line = line[1:-1]
                segments.append(hangups.ChatMessageSegment(line, is_italic=True))
            else:
                segments.append(hangups.ChatMessageSegment(line))
            segments.append(hangups.ChatMessageSegment('\n', hangups.SegmentType.LINE_BREAK))
    if lines[-1]:
        segments.append(hangups.ChatMessageSegment(lines[-1]))

    return segments


def get_last_recorder(conv_id):
    if conv_id in _last_recorder:
        return _last_recorder[conv_id]


def get_last_recorded(conv_id):
    if conv_id in _last_recorded:
        return _last_recorded[conv_id]


def set_last_recorder(conv_id, last_recorder):
    _last_recorder[conv_id] = last_recorder


def set_last_recorded(conv_id, last_recorded):
    _last_recorded[conv_id] = last_recorded


def change_karma(user_id, karma):
    user_karma = UtilDB.get_value_by_user_id("karma", user_id)
    if user_karma is not None:
        user_karma = user_karma[1]
    else:
        user_karma = 0
    UtilDB.set_value_by_user_id("karma", user_id, "karma", (user_karma + karma))
    return user_karma + karma


def get_current_karma(user_id):
    user_karma = UtilDB.get_value_by_user_id("karma", user_id)
    if user_karma is not None:
        return user_karma[1]
    else:
        return 0


def add_reminder(conv_id, message, time):
    db_file = UtilDB.get_database()
    database = sqlite3.connect(db_file)
    cursor = database.cursor()
    cursor.execute("INSERT INTO reminders VALUES (?, ?, ?)", (conv_id, message, time))
    database.commit()
    database.close()


def get_all_reminders(conv_id=None):
    db_file = UtilDB.get_database()
    database = sqlite3.connect(db_file)
    cursor = database.cursor()
    if not conv_id:
        return cursor.execute("SELECT * FROM reminders").fetchall()
    else:
        return cursor.execute("SELECT * FROM reminders WHERE conv_id = ?", (conv_id,)).fetchall()


def delete_reminder(conv_id, message, time):
    db_file = UtilDB.get_database()
    database = sqlite3.connect(db_file)
    cursor = database.cursor()
    timestamp = datetime.now() + timedelta(seconds=time)
    # I have an issue with the timestamps not being exact. I need a better way of being exact.
    # This should work for most cases, but will fail under some circumstances.
    cursor.execute(
        'DELETE FROM reminders WHERE conv_id = ? AND message = ? AND timestamp - ? <= 20',
        (conv_id, message, timestamp))
    database.commit()
    database.close()