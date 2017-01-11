# Builtin imports
import logging
import time
# Internal imports
import core
from core.plugin_handler import subscribe
import tools

log = logging.getLogger()

def is_reminder(event):
    '''Check to see whether a reminder should be set'''
    event_command = event["command"]
    event_verbs = event["verbs"]
    if "remind" in event_verbs:
        return True
    elif "set a reminder" in event_command.lower():
        return True
    else:
        return False

def text2int(textnum, numwords={}):
    '''Convert a number word like five to an int.
    Courtesy of http://stackoverflow.com/questions/493174/is-there-a-way-to-convert-number-words-to-integers'''
    if not numwords:
      units = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen",
      ]

      tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]

      scales = ["hundred", "thousand", "million", "billion", "trillion"]

      numwords["and"] = (1, 0)
      for idx, word in enumerate(units):    numwords[word] = (1, idx)
      for idx, word in enumerate(tens):     numwords[word] = (1, idx * 10)
      for idx, word in enumerate(scales):   numwords[word] = (10 ** (idx * 3 or 2), 0)

    current = result = 0
    for word in textnum.split():
        if word not in numwords:
          return None

        scale, increment = numwords[word]
        current = current * scale + increment
        if scale > 100:
            result += current
            current = 0

    return result + current

def convert_seconds(ent):
    """Convert a string like '10 minutes' to it's value in seconds """
    ent_words = ent.split(" ")
    # How many instances of time in seconds
    # How long in seconds. With different units this changes
    time_instances = 1
    time_in_seconds = 1
    # Parse time out of the words
    for word in ent_words:
        try:
            word_n = text2int(word)
            if not word_n:
                word_n = int(word)
            log.info("Setting time_instances to {0}".format(word_n))
            time_instances = word_n
        except ValueError:
            word_lower = word.lower()
            if "min" in word_lower:
                log.info("Setting time_in_seconds to 60")
                time_in_seconds = 60
            elif "hour" in word_lower:
                time_in_seconds = 3600
            elif "day" in word_lower:
                time_in_seconds = 86400
    log.debug("Time instances is {0} and time in seconds is {1}".format(
        time_instances, time_in_seconds
    ))
    final_time = time_instances * time_in_seconds
    log.info("Parsed a time of {0} seconds from time {1}".format(
        final_time, ent
    ))
    return final_time

def find_alert(event, time_words):
    '''Try to find the subject of the reminder from the command'''
    sentence = event["command"]
    time_split_raw = sentence.split(time_words)
    time_split = time_split_raw[1]
    before_time = time_split_raw[0]
    #If the text after time_split is longer than 1 character
    #Look for a conjunction and return the sentence after the conjunction
    doc = event["doc"]
    adp_tags = [token.orth_ for token in doc if token.pos_ == "ADP" or token.pos_ == "PART"]
    for token in doc:
        #TODO: take this logging out, too verbose for even debug logs
        token_tag = token.pos_
        #If the word is a coordinating conjunction
        if token_tag == "ADP" or token_tag == "PART":
            #Split the sentence by the conjunction
            token_orth = token.orth_
            log.debug("Token {0} has proper tag".format(token_orth))
            token_split = " "+token_orth+" "
            log.info("Token split is {0}".format(token_split))
            try:
                orth_split = sentence.split(token_split)
                conjunction_split = orth_split[1]
                log.info("Orth split is {0}, conjunction split is {1}".format(orth_split, conjunction_split))
                if (len(conjunction_split) > 1):
                    log.debug(
                        "Token being split by is {0}, split is {1}".format(
                            token_split, conjunction_split
                        )
                    )
                    log.debug("Conjunction split is {0}, removing time words {1} if present".format(
                        conjunction_split, time_words
                    ))
                    if time_words in conjunction_split:
                        time_words_c_split = conjunction_split.split(time_words)
                        time_join = " ".join(time_words_c_split)
                        log.debug("Time words split is {0}, time join is {1}".format(time_words_c_split, time_join))
                        conjunction_split = " ".join(time_words_c_split)
                    log.debug(
                        "After checking for time words conjunction split is {0}, checking for adp tags {1}".format(
                        conjunction_split, adp_tags))
                    for word in conjunction_split.split(" "):
                        if word in adp_tags:
                            conjunction_split = " ".join(conjunction_split.split(word))
                    return conjunction_split
                    #TODO: fix this and then add thread safe error handling
            except IndexError:
                #For some reason the sentence can't be split by the original token
                return False
    if len(str(time_split)) > 1:
        if " " in time_split:
            return time_split.split(" ")[1]
        else:
            return time_split
    return False

@subscribe({"name": "reminder", "check": is_reminder})
def main(event):
    '''Set a reminder using the interface scheduler'''
    event_command = event["command"]
    log.info("In set a reminder with command {0}".format(event_command))
    event_ents = event["ents"]
    log.debug("Event ents are {0}".format(event_ents))
    dates = []
    times = []
    # Look through the recognized entities for dates and times
    for ent_type, ent_word in event_ents.items():
        if ent_type == "DATE":
            dates.append(ent_word)
        elif ent_type == "TIME":
            times.append(ent_word)
    log.debug("Found dates {0} and times {1} in event command {2}".format(
        dates, times, event_command
    ))
    # TODO: ask the user about which time they want to ues
    # TODO: add dates processing
    time_message = times[0]
    time_in_seconds = convert_seconds(time_message)
    #Find the alert text
    alert_text = find_alert(event, time_message)
    if not alert_text:
        alert_text == "Reminder: {0}".format(event_command)
    log.info("Alert text is {0}".format(alert_text))
    #Set the reminder using the events framework
    alert_time = time.time()+time_in_seconds
    log.info("Alert time is {0}, time is {1}, time_in seconds is {2}".format(alert_time, time.time(), time_in_seconds))
    event_id = tools.get_event_uid("notification")
    core.events.append({
        "username": event["session"]["username"],
        "time": time.time()+time_in_seconds,
        "value": alert_text,
        "type": "notification",
        "uid": event_id
    })
    return "Got it. In {0} I'll send you the following reminder: {1}".format(
        time_message, alert_text
    )
