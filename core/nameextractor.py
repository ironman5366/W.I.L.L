contacts = open('core/content/contacts.txt').read().split('\n')
from textblob import TextBlob
import re


def pos(text):
    blob = TextBlob(text)
    lst = blob.tags
    grammar_tags = []
    for i in range(0, len(lst)):
        y = re.findall(r'([N][N][P]*[S]*)+', lst[i][1])
        if len(y) != 0:
            grammar_tags.append(y[0])
        else:
            grammar_tags.append("None")
    return grammar_tags


def name_check(word):
    for item in contacts:
        icontacts = (item).split(':')
        if icontacts[0] == word or icontacts[0].lower() == word:
            word_check = icontacts[0]
            break
        elif word == 'me' or word == 'Me':
            word_check = 'me'
        else:
            word_check = None
    if word_check != None:
        return True
    else:
        return False


def main(text):
    text_words = text.split(" ")
    grammar_tags = pos(text)
    names = []
    for i in range(0, len(grammar_tags)):
        if grammar_tags[i] != "None":
            try:
                word = text_words[i].lower()
                check_flag = name_check(word)
                if check_flag == True:
                    names.append(text_words[i])
            except IndexError:
                pass
    return names
