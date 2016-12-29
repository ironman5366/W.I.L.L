##W.I.L.L

Welcome to the new W.I.L.L

##TODO
- Fix wolfram encoding
- Fix error logging
- Rework db so that it works user by chat id and not username
- Add encryption to db
- Add db backups and restorations when server starts and stops
- Make sure that setup script is running dbsetup
- Add spacy.en.download to setup script
- Add a stop.py that is used by a plugin
- Add message to let user know that bot is ready
- Fix it so that default plugin runs last
- Add new interfaces
- Add code that let's the user interface with local devices


##Setup

sudo pip install -r requirements.txt

python dbsetup.py

python main.py