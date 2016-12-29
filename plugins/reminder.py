# Builtin imports
import logging
# Internal imports
from plugin_handler import subscribe
from interface import set_job

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
    time_split = sentence.split(time_words)[1]
    #If the text after time_split is longer than 1 character
    #Look for a conjunction and return the sentence after the conjunction
    doc = event["doc"]
    for token in doc:
        #TODO: take this logging out, too verbose for even debug logs
        token_tag = token.pos_
        #If the word is a coordinating conjunction
        if token_tag == "ADP":
            #Split the sentence by the conjunction
            token_orth = token.orth_
            log.debug("Token {0} has proper tag".format(token_orth))
            try:
                conjunction_split = sentence.split(token_orth)[1]
                if len(conjunction_split) > 1:
                    return conjunction_split
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
    time = times[0]
    time_in_seconds = convert_seconds(time)
    #Find the alert text
    alert_text = find_alert(event, time)
    if not alert_text:
        alert_text == "Reminder: {0}".format(event_command)
    log.info("Alert text is {0}".format(alert_text))
    #Set the reminder using interface.set_job
    set_job(
        event["update"],
        time_in_seconds,
        event["job_queue"],
        event["chat_data"],
        alert_text
    )
    return "Got it. In {0} I'll let you know to {1}".format(
        time, alert_text
    )
