contacts = open('contacts.txt').read().split('\n')
import re


def name_check(word):
    '''Does the actual searching through of the contacts'''
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
    '''Prepares the words for searching'''
    text_words = text.split(" ")
    names = []
    for i in range(0, len(text_words)):
        try:
            word = text_words[i].lower()
            check_flag = name_check(word)
            if check_flag == True:
                names.append(text_words[i])
        except IndexError:
            pass
    return names
