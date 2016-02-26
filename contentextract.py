import re
import string
from logs import logs as log
from dateutil.parser import parse

import nameextractor
logs = log()


def Name_Extract(sentence):
    '''Use nameextractor.py to try to find names'''
    names = nameextractor.main(sentence)
    return names


def Timedate_Extract(sentence):
    '''Find dates and times'''
    lst = (
        'today', 'tomorrow', 'yesterday', 'am', 'a.m', 'a.m.', 'pm', 'p.m', 'p.m.', 'january', 'february', 'march',
        'april',
        'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december', 'Today', 'Tomorrow',
        'Yesterday',
        'AM', 'A.M', 'A.M.', 'PM', 'P.M', 'P.M.', 'January', 'February', 'March', 'April', 'May', 'June', 'July',
        'August',
        'September', 'October', 'November', 'December')
    try:
        for i in lst:
            if i in sentence:
                p = parse(sentence, fuzzy=True)
                td_lst = str(p).split(" ")
                date_lst = td_lst[0].split("-")
                if "tomorrow" in sentence:
                    date_lst[2] = int(date_lst[2]) + 1

                elif "yesterday" in sentence:
                    date_lst[2] = int(date_lst[2]) - 1

                p = [str(date_lst[0]) + "-" + str(date_lst[1]) +
                     "-" + str(date_lst[2]), td_lst[1]]
                break
            else:
                p = "None"
        return p

    except ValueError:
        pass
        return "None"


def Email_Extract(sentence):
    '''Use regex to find emails'''
    expression = re.compile(r"(\S+)@(\S+)")
    result = expression.findall(sentence)
    if result != []:
        return result
    else:
        return "None"


def Phone_Extract(sentence):
    '''Use regex to find phone numbers'''
    reg = re.compile(".*?(\(?\d{3}\D{0,3}\d{3}\D{0,3}\d{4}).*?", re.S)
    num = reg.findall(sentence)
    if num != []:
        return num
    else:
        return "None"


def main(sentence):
    '''Extract data from command'''
    SKtime_date = Timedate_Extract(sentence)
    if SKtime_date != "None":
        SKdate = SKtime_date[0]
        SKtime = SKtime_date[1]
    else:
        SKdate = "None"
        SKtime = "None"
    SKemail = Email_Extract(sentence)
    if SKemail != "None":
        SKemail = SKemail[0][0] + "@" + SKemail[0][1]
    SKphonenumbers = Phone_Extract(sentence)
    if SKphonenumbers != "None":
        SKphonenumbers = SKphonenumbers[0]
    SKnames = Name_Extract(sentence)
    if str(SKnames) != "None":
        names = ""
        for i in SKnames:
            names = names + "" + i
    else:
        names = "None"
    alphabet = list(string.ascii_lowercase)
    if names not in alphabet:
        names = "None"
    data = "Time: " + SKtime + "\n" + "Date: " + SKdate + "\n" + "Email: " + \
        SKemail + "\n" + "Phone: " + SKphonenumbers + "\n" + "Names: " + names
    f = open("content.txt", 'w+')
    f.write(data)
    f.close()
