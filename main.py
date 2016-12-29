#Builtin modules
import logging
import os
import sys
import json

#Internal modules
import interface
import plugin_handler
import parser

#External imports
import dataset

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filemode='w',filename="will.log")

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

#While this is True, W.I.L.L will keep running
will = True
DB_URL = None
DB = None

def shutdown():
    global will
    will = False
    #TODO: figure out what's keeping threads awake, fix it and change os._exit() to sys.exit()
    #sys.exit()
    os._exit(1)
class main():
    '''Start W.I.L.L and determine data status'''
    def __init__(self):
        '''Call starting functions'''
        #Bot token should be held in a file named token.txt
        if os.path.isfile('will.conf'):
            conf_data = json.loads(open('will.conf').read())
            token = conf_data["bot_token"]
            db_url = conf_data["db_url"]
            global DB_URL
            DB_URL = db_url
            log.info("Bot token is {0}".format(token))
            log.info("Initializing the database")
            global DB
            DB = dataset.connect(DB_URL)
            log.info("Loading plugins")
            plugin_handler.load('plugins')
            #Initialize spacy
            log.info("Starting spacy nlp parser")
            parser.initialize()
            log.info("Starting the telegram interface")
            #Start the telegram bot
            interface.initialize(token)
        else:
            log.error('''
            Couldn't find will.conf. Please create a file named will.conf in a json format defining your database url
            and telegram bot token.
            ''')
if __name__ == "__main__":
    log = logging.getLogger()
    log.addHandler(ch)
    log.info("Starting W.I.L.L")
    main()