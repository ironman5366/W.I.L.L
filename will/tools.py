# Builtin imports
import logging

try:
    import queue as Queue
except ImportError:
    import Queue

# External imports
import spacy
import validators

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


def sites_validator(s):
    if type(s) == dict:
        validations = []
        for k, v in s.items():
            validations.append(type(k) == str)
            validations.append(sites_validator(v))
        return all(validations)
    else:
        return validators.url(s)
