# Internal imports
from plugin_handler import subscribe

# External imports
import wolframalpha
import dataset

# Builtin imports
import logging

log = logging.getLogger()


def search_wolfram(query, api_key):
    '''Search wolframalpha'''
    client = wolframalpha.Client(api_key)
    # Santize query
    query = str(query).decode('ascii', 'ignore')
    res = client.query(query)
    try:
        next_result = next(res.results).text
        log.info("Wolfram result is {0}".format(next_result))
        if next_result:
            # Sanitze result
            result = next_result.encode('ascii', 'ignore')
            return next_result
        else:
            return False
    except StopIteration:
        log.error("StopIteration raised with wolfram query {0}".format(
            query
        ))
        return False
    except AttributeError:
        return False


def is_search(event):
    '''Determine whether it's a search command'''
    command = event["command"]
    if "search" in event["verbs"]:
        return True
    question_words = [
        "what",
        "when",
        "why",
        "how",
        "who",
        "are",
        "is"
    ]
    first_word = command.split(" ")[0].lower()
    log.debug("First word in command is {0}".format(first_word))
    if first_word in question_words:
        return True
    return False


@subscribe({"name": "search", "check": is_search})
def main(data):
    '''Start the search'''
    query = data["command"]
    log.info("In main search function with query {0}".format(query))
    db = dataset.connect('sqlite:///will.db')
    user_table = db["userdata"].find_one(username=data["update"].message.from_user.username)
    answer = False
    if "wolfram_key" in user_table.keys():
        log.info("Found wolframa key")
        wolfram_key = user_table["wolfram_key"]
        log.debug("Wolfram key is {0} for user {1}".format(
            wolfram_key, data["update"].message.from_user.username
        ))
        wolfram_response = search_wolfram(query, wolfram_key)
        # If it found an answer answer will be set to that, if not it'll still be false
        answer = wolfram_response
    if answer:
        return answer
    else:
        # TODO: google search
        return "Couldn't find an answer on wolframalpha. Google and wikipedia search coming soon"
