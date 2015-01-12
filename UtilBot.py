from bisect import bisect_left
from urllib import request
from bs4 import BeautifulSoup, Tag
import re

__author__ = 'wardellchandler'


# To keep from crowding up the handlers.py handle method, try to out source to here.
class UtilBot:
    words = open("wordlist.txt")
    list = []
    for line in words:
        list.append(line.strip('\n'))
    list.sort()

    def __init__(self):
        self.names = []
        self.names.append("WHISTLE")
        self.names.append("BOT")
        self.names.append("WHISTLEBOT")
        self.names.append("ROBOT")
        self.names.append("COI")
        self.nameregex = re.compile('\\b(' + '|'.join(self.names) + ')\\b')

    @staticmethod
    def check(string):
        return string.replace("&#39", "'")

    @staticmethod
    def define(word, num=1):
        if num < 1:
            num = 1
        try:
            url = "http://wordnetweb.princeton.edu/perl/webwn?s=" + word + "&sub=Search+WordNet&o2=&o0=&o8=1&o1=1&o7=&o5=&o9=&o6=&o3=&o4=&h=0000000000"
        except Exception as e:
            print(e)
            return 'Couldn\'t download definition.'
        soup = BeautifulSoup(request.urlopen(url))
        if soup.ul is not None:
            definitions = [x.text for x in list(soup.ul) if isinstance(x, Tag) and x.text != '\n' and x.text != '']
            if len(definitions) >= num:
                return (definitions[num - 1] + '[' + str(num) + ' of ' + str(len(definitions)) + ']')[3:].capitalize()
        return "Couldn\'t download definition."

    @staticmethod
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

    @staticmethod
    def find_next_non_blank(list, start=0):
        for x in range(start + 1, len(list)):
            if isinstance(list[x], tuple):
                tocheck = list[x][0]
            else:
                tocheck = list[x]
            tocheck = tocheck.replace(' ', '')
            if tocheck != '':
                return x

    @staticmethod
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

    @staticmethod
    def is_haiku(message):
        message = message.lower().replace('\xa0', " ")
        import string

        for c in string.punctuation:
            message = message.replace(c, "")
        words = re.split('\s+', message)
        total = 0
        for word in words:
            total += UtilBot.syllable_count(word)
        return True if total == 17 else False

    @staticmethod
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
            total += UtilBot.syllable_count(words[index])
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

    @staticmethod
    def binary_search(a, x, lo=0, hi=None):
        hi = hi if hi is not None else len(a)
        pos = bisect_left(a, x, lo, hi)
        return pos if pos != hi and a[pos] == x else ~pos


    @staticmethod
    def add_word(word):
        pos = UtilBot.binary_search(UtilBot.list, word)
        if pos > -1:
            return
        UtilBot.list.insert(~pos, word)
        UtilBot.words = open('wordlist.txt', 'w+')
        UtilBot.words.seek(0)
        for word in UtilBot.list:
            UtilBot.words.write(word + '\n')
        UtilBot.words.close()


    def unhashtag(self, message):
        hashtagged = str(message)
        withspaces = ""
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