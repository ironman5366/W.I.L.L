'''Setup the database when W.I.L.L is installed'''
import dataset

db = dataset.connect('sqlite:///will.db')

key_table = db["public_keys"]

bot_key = None
while not bot_key:
    bot_key = raw_input("Please enter your telegram bot key:")

key_table.insert(dict(kind="telegram", key=bot_key))

