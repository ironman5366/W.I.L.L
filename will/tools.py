#Builtin imports
import logging

try:
    import queue as Queue
except ImportError:
    import Queue
import datetime
import string

#External imports
import spacy

log = logging.getLogger()

command_nums = {}

parser = None

def load_spacy(lang="en"):
    global parser
    parser = spacy.load(lang)

def load():
    log.debug("Loading spacy")
    load_spacy()

def ascii_encode(a):
    return a.encode('ascii', 'ignore')