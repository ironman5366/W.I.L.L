#Builtin imports
import logging

#External imports
import spacy
import dataset
from spacy.symbols import nsubj, VERB
from spacy.matcher import Matcher

#Internal imports
import plugin_handler

log = logging.getLogger()

nlp = None
matcher = None

def parse(bot, update ,job_queue, chat_data):
    '''Function that calls parsing'''
    db = dataset.connect('sqlite:///will.db')
    command = update.message.text
    username = update.message.from_user.username
    log.info(
        "Parsing command {0} from user {1}".format(
            command, username
        )
     )
    #Pull user data from database
    userdata_table = db['userdata']
    user = userdata_table.find_one(username=username)
    user_first_name = user["first_name"]
    #Parse the command in spacy
    log.info("Running command through nlp")
    doc = nlp(unicode(command))
    verbs = set()
    log.info("Parsing through dependencies")
    #Use synactic dependencies to look at the words
    for possible_subject in doc:
        if possible_subject.dep == nsubj and possible_subject.head.pos == VERB:
            verbs.add(possible_subject.head.lemma_.lower())
    log.info("Finished parsing dependencies, parsing ents")
    ents = {}
    #Use spacy's ent recognition
    for ent in doc.ents:
        ents.update({
            ent.label_:ent.text
        })
    log.info("Finished parsing ents")
    command_data = {
        "command": command,
        "bot": bot,
        "update": update,
        "job_queue": job_queue,
        "chat_data": chat_data,
        "verbs": verbs,
        "ents": ents,
        "doc": doc
    }
    log.info("Finished parsing command_data, sending it into events queue")
    log.debug(command_data)
    plugin_handler.subscriptions().send_event(command_data)


def initialize():
    global nlp
    global matcher
    nlp = spacy.load('en')
    matcher = Matcher(nlp.vocab)