#Builtin imports
import logging

try:
    import queue as Queue
except ImportError:
    import Queue

#External imports
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