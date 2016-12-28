#Quick utility for backing up and exporting userdata.
#IMPORTANT: This offers no security and should not be used unless user data is being encrypted seperately
import dataset

db = dataset.connect('sqlite:///will.db')

#Export data
result = db['userdata'].all()
dataset.freeze(result, format='json', filename='users.json')