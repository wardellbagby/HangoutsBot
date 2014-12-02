import re

__author__ = 'cbagby'


class BotCommands:
    def __init__(self):
        self.names = []
        self.names.append("WHISTLE")
        self.names.append("BOT")
        self.names.append("WHISTLEBOT")
        self.names.append("ROBOT")
        self.names.append("COI")
        self.nameregex = re.compile('(' + '|'.join(self.names) + ')[\s\.\?!:\',\";]+')
        self.words = open("wordlist.txt")
        self.list = []
        for line in self.words:
            self.list.append(line.strip('\n'))

    def unhashtag(self, message):
        hashtagged = str(message)
        withspaces = ""
        if hashtagged[0] == '#':
            hashtagged = hashtagged[1:]
        x = len(hashtagged)
        while x > 0:
            if hashtagged[0:x].upper() in (word.upper() for word in self.list):
                withspaces += hashtagged[0:x] + " "
                hashtagged = hashtagged[x:]
                x = len(hashtagged)
            else:
                x -= 1
        return "Unhashtagged: " + withspaces + ("[" + hashtagged + "]" if len(hashtagged) > 0 else "").title()
