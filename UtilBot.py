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
            if not str.isspace(list[x][0]):
                return x



