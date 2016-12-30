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

def command(bot, update ,job_queue, chat_data):
    '''Control the processing of the command'''
    #Call the parser
    parse_data = parser.parse(bot,update,job_queue,chat_data)
    log.info("Nlp parsing finished, adding data to event queue")
    plugin_handler.subscriptions.send_event(parse_data)

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
            log.info("In main, db tables are {0}".format(DB.tables))
            #Define the database in plugin_handler
            log.info("Setting plugin handler database")
            plugin_handler.DB = DB
            log.info("Loading plugins")
            plugin_handler.load('plugins', DB)
            #Initialize spacy
            log.info("Starting spacy nlp parser")
            parser.initialize()
            log.info("Starting the telegram interface")
            #Start the telegram bot
            interface.initialize(token, DB)
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