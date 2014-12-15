from bisect import bisect_left
import re

__author__ = 'cbagby'


class BotCommands:
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
    def binary_search(a, x, lo=0, hi=None):
        hi = hi if hi is not None else len(a)
        pos = bisect_left(a, x, lo, hi)
        return pos if pos != hi and a[pos] == x else ~pos


    @staticmethod
    def add_word(word):
        pos = BotCommands.binary_search(BotCommands.list, word)
        if pos > -1:
            return
        BotCommands.list.insert(~pos, word)
        BotCommands.words = open('wordlist.txt', 'w+')
        BotCommands.words.seek(0)
        for word in BotCommands.list:
            BotCommands.words.write(word + '\n')
        BotCommands.words.close()


    def unhashtag(self, message):
        hashtagged = str(message)
        withspaces = ""
        if hashtagged[0] == '#':
            hashtagged = hashtagged[1:]
        x = len(hashtagged)
        while x > 0:
            if self.binary_search(self.list, hashtagged[0:x].lower()) > -1:
                withspaces += hashtagged[0:x] + " "
                hashtagged = hashtagged[x:]
                x = len(hashtagged)
            else:
                x -= 1
        return "Unhashtagged: " + withspaces + ("[" + hashtagged + "]" if len(hashtagged) > 0 else "").title()
