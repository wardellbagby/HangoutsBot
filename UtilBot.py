from urllib import request
from xml.dom import minidom

__author__ = 'wardellchandler'


# To keep from crowding up the handlers.py handle method, try to out source to here.
class UtilBot:
    def __init__(self):
        UtilBot.words = open("wordlist.txt")
        UtilBot.list = []
        for line in UtilBot.words:
            UtilBot.list.append(line.strip('\n'))

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
        return "Unhashtagged: " + withspaces + "[" + hashtagged + "]".title()

    @staticmethod
    def check(string):
        return string.replace("&#39", "'")

    @staticmethod
    def search(word, num=1):
        if num < 1:
            num = 1
        try:
            url = "http://services.aonaware.com/DictService/DictService.asmx/Define?word=" + word
            reponse = request.urlopen(url)
        except Exception as e:
            print(e)
            return 'Couldn\'t download definition.'
        xmldoc = minidom.parseString(reponse.read().decode())
        deflist = xmldoc.getElementsByTagName('WordDefinition')
        if len(deflist) - 1 > num:
            return str(deflist[num].firstChild.nodeValue) + '[{} out of {}]'.format(num, len(deflist) - 1)
        else:
            return "Couldn't find definition for {}.".format(word)


