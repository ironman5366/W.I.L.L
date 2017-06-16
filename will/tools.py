# Builtin imports
import logging

# External imports
import spacy

log = logging.getLogger()

command_nums = {}

parser = None


def load_spacy(lang):
    global parser
    parser = spacy.load(lang)


def load(lang="en"):
    """
    Load any global tools that are needed.
    Just spacy at the moment
    :param lang: The language model to use for spacy

    """
    log.debug("Loading spacy")
    load_spacy(lang)


def ascii_encode(a):
    return a.encode('ascii', 'ignore')


def location_validator(l):
    # Check proper lat/long format
    if type(l) == dict:
        l_keys = l.keys()
        if "latitude" in l_keys and "longitude" in l_keys:
            if type(l["latitude"]) == float and type(l["longitude"]) == float:
                return True
            else:
                return False
        else:
            return False
    else:
        return False


def load_key(key_name, graph, load_url=False):
    """
    Load an API key from the database

    :param key_name: The name of the key to load
    :param graph: The datbase instance
    :param load_url: A bool defining whether to load the key
    :return key_value, key_url: The API key and optionally a url
    """
    with graph.session() as session:
        valid_keys = session.run("MATCH (a:APIKey {name: {name}) WHERE a.usages < a.max_usages or a.max_usages is "
                                 "null",
                                 {"name": key_name})
        if valid_keys:
            key = valid_keys[0]
            # Increment the key usage
            key_value = key["value"]
            session.run("MATCH (a:APIKey {value: {value}}) SET a.usages = a.usages+1",
                        {"value": key_value})
            key_url = None
            if load_url:
                key_url = key["url"]
            return key_value, key_url
        else:
            return False, False
