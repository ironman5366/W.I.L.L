#Builtin imports
import logging

#External imports
import spacy
import dataset
from spacy.symbols import nsubj, VERB
from spacy.matcher import Matcher

log = logging.getLogger()

log.debug("In parser, loading model")
try:
    nlp = spacy.load('en')
    log.debug("Loaded model")
    matcher = Matcher(nlp.vocab)
    log.debug("Loaded matcher")
except RuntimeError:
    log.warn("IMPORTANT! spaCy English model is not installed. To functionally use W.I.L.L it needs to be installed with python -m spacy.en.download")
def parse(command_data, session):
    '''Function that calls parsing'''
    command = command_data["command"]
    username = session["username"]
    log.info(
        "Parsing command {0} from user {1}".format(
            command, username
        )
     )
    #Parse the command in spacy
    log.info("Running command through nlp")
    doc = nlp(unicode(command))
    verbs = set()
    log.info("Parsing through dependencies")
    for token in doc:
        if token.pos == VERB:
            verbs.add(token.lemma_.lower())
    log.info("Finished parsing dependencies, parsing ents")
    ents = {}
    #Use spacy's ent recognition
    for ent in doc.ents:
        ents.update({
            ent.label_:ent.text
        })
    log.info("Finished parsing ents")
    event_data = {
        "command": command,
        "session": session,
        "command_data": command_data,
        "verbs": verbs,
        "ents": ents,
        "doc": doc
    }
    log.info("Finished parsing event_data, sending it into events queue")
    log.debug("Event_data is {0}".format(event_data))
    return event_data
