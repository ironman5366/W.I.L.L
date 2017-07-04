# Builtin imports
import logging

# External imports
import spacy

# Internal imports
from will.schema import *

log = logging.getLogger()

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


def load_key(key_name, db, load_url=False):
    """
    Load an API key from the database

    :param key_name: The name of the key to load
    :param db: The database instance
    :param load_url: A bool defining whether to load the key
    :return key_value, key_url: The API key and optionally a url
    """
    session = db()
    valid_keys = session.query(APIKey).filter(APIKey.key_type == key_name, APIKey.usages < APIKey.max_usages).all()
    if valid_keys:
        key = valid_keys[0]
        # Increment the key usage
        key_value = key.value
        key.usages += 1
        key_url = None
        if load_url:
            key_url = key.url
        session.commit()
        return key_value, key_url
    else:
        return False, False
