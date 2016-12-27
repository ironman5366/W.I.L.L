#Builtin modules
import logging
import os
import sys

#Internal modules
import interface
import plugin_handler
import parser

#External imports
import dataset

db = dataset.connect('sqlite:///will.db')
#
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filemode='w',filename="will.log")

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)

def shutdown():
    log.info("Shutting down W.I.L.L")
    sys.exit()

class main():
    '''Start W.I.L.L and determine data status'''
    def __init__(self):
        '''Call starting functions'''
        #Bot token should be held in a file named token.txt
        if "public_keys" in db.tables:
            token = db["public_keys"].find_one(kind="telegram")["key"]
            log.info("Bot token is {0}".format(token))
            log.info("Loading plugins")
            plugin_handler.load('plugins')
            #Initialize spacy
            log.info("Starting spacy nlp parser")
            parser.initialize()
            log.info("Starting the telegram interface")
            #Start the telegram bot
            interface.initialize(token)
        else:
            log.error(
                '''
                Couldn't find the database table containing the api token.
                Please create a public keys table that contains the telegram bot token under bot_token
                '''
            )
if __name__ == "__main__":
    log = logging.getLogger()
    log.addHandler(ch)
    log.info("Starting W.I.L.L")
    main()