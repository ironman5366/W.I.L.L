#External libs
from spacy.en import English

#Builtin libs
import logging
import threading
import time

#Internal libs
import plugin_manager

#Variables to determine if parsing is done
done = {
    "parsing": False,
    "ents": False,
    "structure": False,
    "questions": False,
    "elimination" : False
}
#TODO: add a framework that can discriminate based on where certain tags are

#Currently known plugins
current_plugins = []

#Plugins left in the running
plugins_left = []
'''
plugins_left structure:
[
{"name": "test",
"ents_needed" : ["PERSON", "PHONE"],
"structure" : {"needed":["VERB"]},
"questions_needed" : True}
]
'''

#Currently known data
current_data = {
    "ents": {},
    "structure": {
        {"tags": {}}
    },
    "questions": False
}

#Define an english parser
parser = English()

#TODO: consider adding a timer so parsing doesn't take too long

class main():
    '''Nlp functions'''
    def elimination(self):
        '''Thread to eliminate plugins that are incompatible'''
        current_plugins = plugin_manager.reader().get_plugins()
        plugins_left = current_plugins
        #While the parsing part of the program isn't finished
        while not done["parsing"]:
            #Iterate over the plugins that haven't been eliminated
            for plugin in plugins_left:
                #Check if required entities have been obtained
                if done["ents"]:
                    logging.info("Ents is done, checking")
                    ents_category = plugin['ents_needed']
                    if ents_category:
                        for ent in ents_category:
                            if ent not in current_data["ents"].values():
                                logging.info("Removing plugin {0} because of ent {1}".format(str(plugin['name']),str(ent)))
                                plugins_left.remove(plugin)
                                break
                #Check if required tags are had and in the correct order
                if done["structure"]:
                    structure_category = plugin["structure"]
                    if structure_category:
                        struct_needed = structure_category['needed']
                        for tag in struct_needed.keys():
                            if tag not in current_data["structure"]["tags"].values():
                                plugins_left.remove(plugin)
                                break

                #If it needs a question check if there is one
                if done["questions"]:
                    q_category = plugin['questions_needed']
                    if q_category:
                        if not current_data['questions']:
                            plugins_left.remove(plugin)
                            break
            if len(plugins_left == 1):
                done['elimination'] = True
                return plugins_left
        done['elimination'] = True
        return plugins_left
    def entity_recognition(self, parsed_data):
        '''Entity recognition: organizations, people, numbers, etc.'''
        ents = list(parsed_data.ents)
        final_ents ={}
        for entity in ents:
            final_ents.update({' '.join(t.orth_ for t in entity): entity.label_})
        return final_ents
    def POS(self, parsed_data):
        '''POS tagging'''
        tags = {}
        for token in parsed_data:
            tags.update({token.orth_:token.pos})
        return tags
    def question_check(self, sentence):
        '''Check if the sentence is a question'''
        q_words = ["is","are","am","was","were","will","do","does","did","have","had","has","can","could","should","shall","may","might","would","how","who","what","where","when","wouldn't","shouldn't","couldn't","hadn't","didn't","weren't", "don't","doesn't","haven't","can't","wasn't"]
        logging.info('Checking if the sentence is a question')
        first_word = sentence.split(" ")[0].lower()
        return first_word in q_words
    def load(self, text):
        '''Load data into spacy nlp'''
        logging.info("Loading text {0} into spacy.".format(str(text)))
        text = unicode(text, "utf-8")
        parsed_data = parser(text)
        #Return the parsed data
        return parsed_data
    def parse_thread(self, sentence):
        '''Thread in which parsing functions are called'''
        logging.info("In parsing thread")
        #Get spacey loaded data
        parsed_data = self.load(sentence)
        #Threaded functions for each part of the nlp
        def check_keywords(sentence):
            for word in sentence.split(" "):
                
        def get_ents(parsed_data):
            '''Get the entity data'''
            logging.info("Getting entity data")
            ents = self.entity_recognition(parsed_data)
            current_data['ents'] = ents
            done['ents'] = True
            logging.info("Finished getting entity data")
        def get_structure(parsed_data):
            '''Get the POS/Structure data'''
            #This will, at the moment, just append the tags to strucutre without any position data.
            #TODO: improve this
            logging.info("Getting POS tags")
            #Get POS tags
            pos_tags = self.POS(parsed_data)
            current_data['structure']['tags'].update(pos_tags)
            done["structure"] = True
            logging.info("Finished getting POS tags")
        def get_qcheck(sentence):
            '''Get the question data'''
            logging.info("Checking if the command is a question")
            q_check = self.question_check(sentence)
            logging.info("Question check returned {0}".format(str(q_check)))
            current_data["questions"] = q_check
            done["questions"] = True
        #Start all the threads
        ent_thread = threading.Thread(target=get_ents(parsed_data))
        struct_thread = threading.Thread(target=get_structure(parsed_data))
        question_thread = threading.Thread(target=get_qcheck(sentence))
        ent_thread.start()
        struct_thread.start()
        question_thread.start()
        logging.info("Started the parsing threads")
        #Wait for everything to be done
        while not done["structure"] and not done["questions"] and not done["ents"]:
            time.sleep("0.001")
        done["parsing"] = True
    def parse(self, sentence):
        '''Main parsing function'''
        logging.info("In parsing function.")
        logging.info("Sentence is {0}".format(str(sentence)))
        # Start the elimination thread
        logging.info("Starting elimination thread")
        e_thread = threading.Thread(target=self.elimination)
        e_thread.start()
        logging.info("Starting parsing thread")
        p_thread = threading.Thread(target=self.parse_thread(sentence))
        p_thread.start()
        while not done['elimination']:
            time.sleep("0.001")
        return plugins_left
