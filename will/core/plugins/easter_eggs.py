import logging

from will.core.plugin_handler import *
from will.core import arguments
from will import tools

parser = tools.parser

log = logging.getLogger()

easter_eggs = {
    "Who are you?": "I am will, short for Wireless Intelligent Linguistical Liveware",
    "Who created you?": "I was created by Will Beddow (will@willbeddow.com)",
    "Take me to your leader": "I don't have a leader. But you can talk to my creator, Will Beddow (will@willbeddow.com)",
    "Why do you exist": "To kick ass, execute advanced context-aware natural language algorithms, and take names.",
    "What's your name?": "I am will, short for Wireless Intelligent Linguistic Liveware",
    "How old are you?": "will was first thought up in 2014, and will 1.0 was made in the same year. I underwent "
                        "many iterations and changes, and finally, here I am. Fun fact: the current will uses none "
                        "of the original code from will 1.0 ",
    "Hey will": "What's up?",
    "Who is your master?": "I was created by Will Beddow (will@willbeddow.com)"
}


@subscribe
class EasterEggs(Plugin):
    name = "eastereggs"
    eggs = []
    arguments = [arguments.CommandParsed]

    # TODO: write a cleaner implemntation of this
    def check(self, command_obj):
        scores = [command_obj.parsed.similarity(x) for x in self.eggs]
        return max(scores) >= 0.96

    def exec(self, **kwargs):
        scores = {}
        doc = kwargs["CommandParsed"]
        for x_parse in self.eggs:
            scores.update({
                doc.similarity(x_parse): easter_eggs[x_parse.text]
            })
        most_compatible = scores[max(scores)]
        log.debug("Query {0} activated easter egg {1}".format(doc.text, most_compatible))
        response = {
            "data":
                {
                    "type": "success",
                    "id":  "EASTER_EGG_PLUGIN_SUCCESS",
                    "text": most_compatible
                }
        }
        return response

    def __init__(self):
        """
        Run all of the phrases through spacy when it's instantiated so that they don't have to be parsed
        every time
        """
        log.debug("Loading easter eggs into spacy")
        self.eggs = [tools.parser(x) for x in easter_eggs]